"""Installs into a remote venv, with `uv pip` unless use_uv=False.

force=True passes --force-reinstall. It only matters in a reused venv
(create_venv(..., recreate=False)): pip compares versions, not commits, so new code under
the same version would be skipped and the server would keep running the old one.
"""

import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from fabric import Connection

from .models import Venv
from .transfer import upload_directory
from .venv import run_in_venv


def _install_cmd(use_uv: bool, force: bool, target: str) -> str:
    pip = "uv pip" if use_uv else "python -m pip"
    flags = " --force-reinstall" if force else ""
    return f"{pip} install{flags} {target}"


def install_packages(
    conn: Connection,
    venv: Venv,
    packages: List[str],
    use_uv: bool = True,
    verbose: bool = True,
    force: bool = False,
) -> None:
    """Install requirement specifiers from PyPI, e.g. ["fastapi", "requests>=2.31"]."""
    if not isinstance(packages, list) or not all(isinstance(pkg, str) for pkg in packages):
        raise TypeError("packages must be a list of str")
    if not packages or not all(pkg.strip() for pkg in packages):
        raise ValueError("packages must be a non-empty list of non-blank specifiers")

    if verbose:
        print(f"Installing packages in venv: {', '.join(packages)}")
    quoted = " ".join(shlex.quote(pkg) for pkg in packages)
    run_in_venv(conn, venv, _install_cmd(use_uv, force, quoted), verbose=False, hide=True)


def install_local_package(
    conn: Connection,
    venv: Venv,
    local_package_dir: str,
    use_uv: bool = True,
    verbose: bool = True,
    force: bool = False,
) -> None:
    """Upload a local package (pyproject.toml or setup.py at its root) and install it,
    with its dependencies. The remote copy is a fresh temp directory, removed afterwards
    even if the install fails."""
    remote_temp = conn.run("mktemp -d /tmp/pyeasydeploy.XXXXXX", hide=True).stdout.strip()
    try:
        upload_directory(conn, local_package_dir, remote_temp, verbose=verbose)
        if verbose:
            print(f"Installing package from {remote_temp}")
        run_in_venv(conn, venv, _install_cmd(use_uv, force, shlex.quote(remote_temp)),
                    verbose=False, hide=True)
    finally:
        if verbose:
            print(f"Cleaning up {remote_temp}")
        conn.run(f"rm -rf {shlex.quote(remote_temp)}", hide=True, warn=True)


def install_package_from_github(
    conn: Connection,
    venv: Venv,
    github_repo_url: str,
    use_uv: bool = True,
    verbose: bool = True,
    force: bool = False,
) -> None:
    """Install from a repository the server itself can clone. For private ones, see
    install_package_from_private_github."""
    if verbose:
        print(f"Installing package from GitHub repo: {github_repo_url}")
    run_in_venv(conn, venv, _install_cmd(use_uv, force, shlex.quote("git+" + github_repo_url)),
                verbose=False, hide=True)


def install_package_from_private_github(
    conn: Connection,
    venv: Venv,
    github_repo_url: str,
    branch: str = None,
    use_uv: bool = True,
    verbose: bool = True,
    force: bool = False,
) -> None:
    """Clone on this machine, with your own git credentials, then upload the source and
    install it. The server never needs access to GitHub."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_name = github_repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
        local_clone = Path(tmpdir) / repo_name

        clone_cmd = ["git", "clone", "--depth", "1"]
        if branch:
            clone_cmd += ["--branch", branch]
        clone_cmd += [github_repo_url, str(local_clone)]

        if verbose:
            print(f"Cloning {github_repo_url} locally...")
        result = subprocess.run(clone_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")

        shutil.rmtree(local_clone / ".git", ignore_errors=True)
        install_local_package(conn, venv, str(local_clone),
                              use_uv=use_uv, verbose=verbose, force=force)
