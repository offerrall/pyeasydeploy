import shlex
from typing import Any

from fabric import Connection

from .models import PythonInstance, Venv
from .transfer import check_destination


def create_venv(
    conn: Connection,
    python: PythonInstance,
    path: str,
    verbose: bool = True,
    recreate: bool = True,
) -> Venv:
    """Create a venv at path, with uv installed in it.

    Destructive by default: an existing venv is removed and rebuilt, so its contents
    depend only on this deploy. recreate=False reuses it, which is faster in
    development, but pip may then skip new code under an unchanged version (see
    `force` in the install functions).
    """
    venv = Venv(python=python, path=path)
    # The model only checks the path is absolute; "/" or "/home" would be wiped.
    if recreate:
        check_destination(venv.path)

    quoted_path = shlex.quote(venv.path)
    exists = conn.run(f"test -d {quoted_path}", warn=True, hide=True)

    if exists.ok and not recreate:
        if verbose:
            print(f"Virtual environment already exists at {venv.path}, reusing.")
    else:
        if exists.ok:
            if verbose:
                print(f"Removing existing virtual environment at {venv.path}")
            conn.run(f"rm -rf {quoted_path}", hide=True)
        conn.run(f"{shlex.quote(python.executable)} -m venv {quoted_path}", hide=not verbose)
        if verbose:
            print(f"Created virtual environment at {venv.path} using Python {python.version}")

    if verbose:
        print("Ensuring uv is installed in venv...")
    run_in_venv(conn, venv, "python -m pip install -q uv", verbose=False)
    return venv


def delete_venv(conn: Connection, venv: Venv, verbose: bool = True) -> None:
    check_destination(venv.path)
    conn.run(f"rm -rf {shlex.quote(venv.path)}", hide=True)
    if verbose:
        print(f"Deleted virtual environment at {venv.path}")


def run_in_venv(
    conn: Connection,
    venv: Venv,
    command: str,
    verbose: bool = True,
    hide: bool = False,
) -> Any:
    """Run a shell command with the venv's bin/ first in PATH, as `activate` would.

    The command goes to the remote shell as is: quoting inside it is up to the caller.
    """
    env_prefix = (
        f"export VIRTUAL_ENV={shlex.quote(venv.path)} && "
        f"export PATH={shlex.quote(venv.path + '/bin')}:\"$PATH\""
    )
    if verbose:
        print(f"Running in venv: {command}")
    return conn.run(f"{env_prefix} && {command}", hide=hide)
