"""Remote virtual environment management for pyeasydeploy.

Creates, deletes and runs commands inside venvs on the remote host.
No 'source activate' is used: activation is just PATH manipulation,
so we do exactly that — robust under any POSIX shell, no bash-isms.
"""

import shlex
from typing import Any

from fabric import Connection

from .models import PythonInstance, VenvPython
from pathlib import PurePosixPath


def create_venv(
    conn: Connection,
    python_instance: PythonInstance,
    venv_path: str,
    verbose: bool = True,
) -> VenvPython:
    """Create a virtual environment on the remote host (idempotent).

    If the directory already exists it is reused, not recreated.
    The 'uv' installer is ensured inside the venv either way, so
    package functions can rely on it.

    Args:
        conn: Connection to the remote host.
        python_instance: Interpreter to create the venv with. Trusted
            as-is: if you built it by hand, you vouch for it.
        venv_path: Absolute remote path for the venv,
            e.g. "/home/app/venvs/myapp".
        verbose: Print progress to stdout.

    Returns:
        A validated VenvPython bound to the interpreter and path.

    Raises:
        TypeError / ValueError: From VenvPython validation, e.g. if
            venv_path is not absolute.
    """
    # Build the model FIRST: its validation rejects bad paths before
    # any remote command runs.
    venv = VenvPython(
        venv_name=PurePosixPath(venv_path).name,
        python_instance=python_instance,
        venv_path=venv_path,
    )

    quoted_path = shlex.quote(venv.venv_path)
    exists = conn.run(f"test -d {quoted_path}", warn=True, hide=True)

    if exists.ok:
        if verbose:
            print(f"Virtual environment already exists at {venv.venv_path}, reusing.")
    else:
        cmd = f"{shlex.quote(python_instance.executable)} -m venv {quoted_path}"
        conn.run(cmd, hide=not verbose)
        if verbose:
            print(
                f"Created virtual environment at {venv.venv_path} "
                f"using Python {python_instance.version}"
            )

    if verbose:
        print("Ensuring uv is installed in venv...")
    run_in_venv(conn, venv, "python -m pip install -q uv", verbose=False)

    return venv


def delete_venv(conn: Connection, venv: VenvPython, verbose: bool = True) -> None:
    """Delete a virtual environment from the remote host.

    Args:
        conn: Connection to the remote host.
        venv: The environment to delete.
        verbose: Print progress to stdout.
    """
    conn.run(f"rm -rf {shlex.quote(venv.venv_path)}", hide=True)
    if verbose:
        print(f"Deleted virtual environment at {venv.venv_path}")


def run_in_venv(
    conn: Connection,
    venv: VenvPython,
    command: str,
    verbose: bool = True,
    hide: bool = False,
) -> Any:
    """Run a shell command with the venv's bin/ first in PATH.

    Equivalent to what 'source activate' achieves (PATH precedence and
    VIRTUAL_ENV), without depending on bash or on the activate script:
    'python', 'pip', 'uv' and any console script resolve to the venv's
    own binaries.

    The command string is passed to the remote shell as-is: quoting of
    its internals is the caller's responsibility (it is a command, not
    an argument).

    Args:
        conn: Connection to the remote host.
        venv: Environment whose binaries take precedence.
        command: Shell command to run, e.g. "python -m myapp --check".
        verbose: Print the command before running it.
        hide: Hide the remote command's output (passed to Fabric).

    Returns:
        The Fabric result object of the executed command.
    """
    bin_dir = f"{venv.venv_path}/bin"
    env_prefix = (
        f"export VIRTUAL_ENV={shlex.quote(venv.venv_path)} && "
        f"export PATH={shlex.quote(bin_dir)}:\"$PATH\""
    )
    if verbose:
        print(f"Running in venv: {command}")
    return conn.run(f"{env_prefix} && {command}", hide=hide)