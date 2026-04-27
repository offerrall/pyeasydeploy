import shutil
import subprocess
import tempfile
from pathlib import Path
from fabric import Connection

from . import VenvPython
from .transfer import upload_directory
from .venv import run_in_venv

def _pip(use_uv: bool) -> str:
    return "uv pip" if use_uv else "pip"

def install_packages(conn: Connection, venv: VenvPython, packages: list[str], use_uv: bool = False, verbose: bool = True):
    packages_str = " ".join(packages)
    command = f"{_pip(use_uv)} install {packages_str}"
    if verbose: print(f"Installing packages in venv: {packages_str}")
    run_in_venv(conn, venv, command, verbose=False)

def install_local_package(conn: Connection, venv: VenvPython, local_package_dir: str, use_uv: bool = False, verbose: bool = True):
    package_name = Path(local_package_dir).name
    remote_temp_dir = f"/tmp/{package_name}"
    
    upload_directory(conn, local_package_dir, remote_temp_dir, verbose=verbose)
    
    command = f"{_pip(use_uv)} install {remote_temp_dir}"
    if verbose: print(f"Installing package from {remote_temp_dir}")
    run_in_venv(conn, venv, command, verbose=False)

    if verbose: print(f"Cleaning up {remote_temp_dir}")
    conn.run(f"rm -rf {remote_temp_dir}", hide=True)

def install_package_from_github(conn: Connection, venv: VenvPython, github_repo_url: str, use_uv: bool = False, verbose: bool = True):
    command = f"{_pip(use_uv)} install git+{github_repo_url}"
    if verbose: print(f"Installing package from GitHub repo: {github_repo_url}")
    run_in_venv(conn, venv, command, verbose=False)

def install_package_from_private_github(conn: Connection, venv: VenvPython, github_repo_url: str, branch: str | None = None, use_uv: bool = False, verbose: bool = True):
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_name = github_repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        local_clone = Path(tmpdir) / repo_name

        clone_cmd = ["git", "clone", "--depth", "1"]
        if branch:
            clone_cmd += ["--branch", branch]
        clone_cmd += [github_repo_url, str(local_clone)]

        if verbose: print(f"Cloning {github_repo_url} locally...")
        result = subprocess.run(clone_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")

        shutil.rmtree(local_clone / ".git", ignore_errors=True)

        install_local_package(conn, venv, str(local_clone), use_uv=use_uv, verbose=verbose)