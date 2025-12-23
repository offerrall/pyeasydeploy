from pathlib import PurePosixPath
from fabric import Connection

from . import PythonInstance, VenvPython

def create_venv(conn: Connection, python_instance: PythonInstance, venv_path: str, verbose: bool = True) -> VenvPython:
    exists = conn.run(f"test -d {venv_path}", warn=True, hide=True)

    if exists.ok:
        if verbose:
            print(f"Virtual environment already exists at {venv_path}, skipping creation.")
    else:
        cmd = f"{python_instance.executable} -m venv {venv_path}"
        conn.run(cmd)
        if verbose:
            print(f"Created virtual environment at {venv_path} using Python {python_instance.version}")

    return VenvPython(
        python_instance=python_instance, 
        venv_path=venv_path, 
        venv_name=PurePosixPath(venv_path).name
    )

def delete_venv(conn: Connection, venv: VenvPython, verbose: bool = True):
    conn.run(f"rm -rf {venv.venv_path}")
    if verbose:
        print(f"Deleted virtual environment at {venv.venv_path}")

def run_in_venv(conn: Connection, venv: VenvPython, command: str, verbose: bool = True):
    activate_prefix = f"source {venv.venv_path}/bin/activate"
    full_command = f"{activate_prefix} && {command}"
    if verbose: 
        print(f"Running in venv: {command}")
    return conn.run(full_command)