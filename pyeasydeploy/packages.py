from pathlib import Path
from fabric import Connection

from . import VenvPython
from .transfer import upload_file, upload_directory
from .venv import run_in_venv

def install_packages(conn: Connection, venv: VenvPython, packages: list[str], verbose: bool = True):
    packages_str = " ".join(packages)
    command = f"pip install {packages_str}"
    if verbose: print(f"Installing packages in venv: {packages_str}")
    run_in_venv(conn, venv, command, verbose=False)

def install_local_package(conn: Connection, venv: VenvPython, local_package_dir: str, verbose: bool = True):
    package_name = Path(local_package_dir).name
    remote_temp_dir = f"/tmp/{package_name}"
    
    upload_directory(conn, local_package_dir, remote_temp_dir, verbose=verbose)
    
    command = f"pip install {remote_temp_dir}"
    if verbose: print(f"Installing package from {remote_temp_dir}")
    run_in_venv(conn, venv, command, verbose=False)

    if verbose: print(f"Cleaning up {remote_temp_dir}")
    conn.run(f"rm -rf {remote_temp_dir}", hide=True)

def install_package_from_github(conn: Connection, venv: VenvPython, github_repo_url: str, verbose: bool = True):
    command = f"pip install git+{github_repo_url}"
    if verbose: print(f"Installing package from GitHub repo: {github_repo_url}")
    run_in_venv(conn, venv, command, verbose=False)