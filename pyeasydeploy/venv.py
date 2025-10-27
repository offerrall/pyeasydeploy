from pathlib import PurePosixPath
from fabric import Connection

from . import PythonInstance, VenvPython

def create_venv(conn: Connection, python_instance: PythonInstance, venv_path: str, verbose: bool = True) -> VenvPython:
    cmd = f"{python_instance.executable} -m venv {venv_path}"
    conn.run(cmd)
    if verbose: print(f"Created virtual environment at {venv_path} using Python {python_instance.version}")
    return VenvPython(python_instance=python_instance, venv_path=venv_path, venv_name=PurePosixPath(venv_path).name)

def run_in_venv(conn: Connection, venv: VenvPython, command: str, verbose: bool = True):
    activate_prefix = f"source {venv.venv_path}/bin/activate"
    full_command = f"{activate_prefix} && {command}"
    if verbose: print(f"Running in venv: {command}")
    return conn.run(full_command)