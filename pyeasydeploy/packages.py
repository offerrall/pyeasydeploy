"""Package installation into remote virtual environments.

All installs run inside the venv (see run_in_venv) and use 'uv pip'
by default for speed, falling back to plain pip on request.

The private-GitHub flow clones LOCALLY with your own git credentials
and uploads the result: the server never needs access to your GitHub.
"""

import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from fabric import Connection

from .models import VenvPython
from .transfer import upload_directory
from .venv import run_in_venv


def _install_cmd(use_uv: bool, force: bool, target: str) -> str:
    """Build the install command line (target must be quoted already)."""
    pip = "uv pip" if use_uv else "python -m pip"
    flags = " --force-reinstall" if force else ""
    return f"{pip} install{flags} {target}"


def _make_remote_tempdir(conn: Connection) -> str:
    """Create a unique temporary directory on the remote host.

    Unique per call: concurrent deploys of the same package to the
    same host can never collide.
    """
    result = conn.run("mktemp -d /tmp/pyeasydeploy.XXXXXX", hide=True)
    return result.stdout.strip()


def install_packages(
    conn: Connection,
    venv: VenvPython,
    packages: List[str],
    use_uv: bool = True,
    verbose: bool = True,
    force: bool = False,
) -> None:
    """Install packages from PyPI into the remote venv.

    Args:
        conn: Connection to the remote host.
        venv: Target virtual environment.
        packages: Requirement specifiers, e.g. ["fastapi",
            "uvicorn[standard]", "requests>=2.31"].
        use_uv: Install with 'uv pip' (fast, default) instead of pip.
        verbose: Print progress to stdout.
        force: Pass --force-reinstall, reinstalling even when the
            requirement is already satisfied. Not needed with a freshly
            created venv (the default); useful with create_venv(...,
            recreate=False), where pip would otherwise keep a package
            whose version did not change.

    Raises:
        TypeError: If packages is not a list of str.
        ValueError: If packages is empty or contains blank entries.
    """
    if not isinstance(packages, list) or not all(
        isinstance(pkg, str) for pkg in packages
    ):
        raise TypeError("packages must be a list of str")
    if not packages or not all(pkg.strip() for pkg in packages):
        raise ValueError("packages must be a non-empty list of non-blank specifiers")

    quoted = " ".join(shlex.quote(pkg) for pkg in packages)
    if verbose:
        print(f"Installing packages in venv: {', '.join(packages)}")
    run_in_venv(conn, venv, _install_cmd(use_uv, force, quoted),
                verbose=False, hide=True)


def install_local_package(
    conn: Connection,
    venv: VenvPython,
    local_package_dir: str,
    use_uv: bool = True,
    verbose: bool = True,
    force: bool = False,
) -> None:
    """Upload a local package directory and install it into the venv.

    The directory must be an installable package (pyproject.toml or
    setup.py at its root): its declared dependencies are installed
    automatically. It is uploaded to a unique remote temp directory,
    installed, and the temp directory is removed even if the install
    fails.

    Args:
        conn: Connection to the remote host.
        venv: Target virtual environment.
        local_package_dir: Path to the local package root.
        use_uv: Install with 'uv pip' (fast, default) instead of pip.
        verbose: Print progress to stdout.
        force: Pass --force-reinstall. THE COMMON CASE for local
            packages when reusing a venv (create_venv(...,
            recreate=False)): pip compares versions, not commits, so
            new code shipped under the same version number is ignored
            and the server keeps running the old one, silently.

    Raises:
        FileNotFoundError: If local_package_dir does not exist (from
            upload_directory).
    """
    remote_temp = _make_remote_tempdir(conn)
    try:
        upload_directory(conn, local_package_dir, remote_temp, verbose=verbose)
        if verbose:
            print(f"Installing package from {remote_temp}")
        run_in_venv(conn, venv,
                    _install_cmd(use_uv, force, shlex.quote(remote_temp)),
                    verbose=False, hide=True)
    finally:
        if verbose:
            print(f"Cleaning up {remote_temp}")
        conn.run(f"rm -rf {shlex.quote(remote_temp)}", hide=True, warn=True)


def install_package_from_github(
    conn: Connection,
    venv: VenvPython,
    github_repo_url: str,
    use_uv: bool = True,
    verbose: bool = True,
    force: bool = False,
) -> None:
    """Install a package from a public GitHub repository.

    The REMOTE host clones the repo (it must be public, or reachable
    from the server). For private repos, use
    install_package_from_private_github instead.

    Args:
        conn: Connection to the remote host.
        venv: Target virtual environment.
        github_repo_url: Repository URL, e.g.
            "https://github.com/user/repo".
        use_uv: Install with 'uv pip' (fast, default) instead of pip.
        verbose: Print progress to stdout.
        force: Pass --force-reinstall. Needed when reusing a venv and
            the branch moved without a version bump: pip compares
            versions, not commits, so the new commit would be ignored
            and the server would keep running the old code.
    """
    if verbose:
        print(f"Installing package from GitHub repo: {github_repo_url}")
    run_in_venv(conn, venv,
                _install_cmd(use_uv, force,
                             shlex.quote("git+" + github_repo_url)),
                verbose=False, hide=True)


def install_package_from_private_github(
    conn: Connection,
    venv: VenvPython,
    github_repo_url: str,
    branch: str = None,
    use_uv: bool = True,
    verbose: bool = True,
    force: bool = False,
) -> None:
    """Install a package from a private GitHub repository.

    Clones LOCALLY (with your machine's git credentials), strips the
    .git directory, uploads the source and installs it. The server
    never needs GitHub access, deploy keys or tokens.

    Args:
        conn: Connection to the remote host.
        venv: Target virtual environment.
        github_repo_url: Repository URL, SSH or HTTPS form.
        branch: Branch or tag to clone. None uses the default branch.
        use_uv: Install with 'uv pip' (fast, default) instead of pip.
        verbose: Print progress to stdout.
        force: Pass --force-reinstall. Needed when reusing a venv and
            the branch moved without a version bump: pip compares
            versions, not commits, so the new commit would be ignored
            and the server would keep running the old code.

    Raises:
        RuntimeError: If the local 'git clone' fails (bad URL, no
            access, branch not found...).
    """
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

        # The .git directory is history + credentials-adjacent metadata:
        # the server needs neither.
        shutil.rmtree(local_clone / ".git", ignore_errors=True)

        install_local_package(conn, venv, str(local_clone),
                              use_uv=use_uv, verbose=verbose, force=force)