import re
from typing import List

from fabric import Connection

from .models import PythonInstance

# Real interpreters only: python3 or python3.11, never python3.11-config or python3-qt.
_INTERPRETER_RE = re.compile(r"^/usr/bin/python3(\.\d+)?$")


def _version_key(instance: PythonInstance) -> tuple:
    return tuple(int(part) for part in instance.version.split("."))


def get_python_instances(conn: Connection, verbose: bool = True) -> List[PythonInstance]:
    """The python3 interpreters in /usr/bin, newest first."""
    if verbose:
        print("Searching for Python instances...")

    # warn=True: an empty glob is reported by the RuntimeError below, not by Fabric.
    result = conn.run("ls -1 /usr/bin/python3* 2>/dev/null", hide=True, warn=True)

    instances = []
    for line in result.stdout.splitlines():
        path = line.strip()
        if not _INTERPRETER_RE.match(path):
            continue
        version = path.rsplit("/", 1)[-1].removeprefix("python")
        instances.append(PythonInstance(version=version, executable=path))
        if verbose:
            print(f"Found Python {version} at {path}")

    if not instances:
        raise RuntimeError(
            "No python3 interpreter found in /usr/bin on the remote "
            "host. Install one (e.g. 'apt install python3') and retry."
        )

    instances.sort(key=_version_key, reverse=True)
    return instances


def get_target_python_instance(
    conn: Connection, target_version: str, verbose: bool = True
) -> PythonInstance:
    """The newest interpreter matching target_version by components.

    "3.1" matches Python 3.1 only, not 3.11; "3" matches any python3.X.
    """
    if not isinstance(target_version, str):
        raise TypeError(f"target_version must be str, got {type(target_version).__name__}")
    try:
        target_parts = tuple(int(p) for p in target_version.strip().split("."))
    except ValueError:
        raise ValueError(
            f"target_version must be dot-separated integers like '3.11', "
            f"got {target_version!r}"
        ) from None

    instances = get_python_instances(conn, verbose=verbose)
    if verbose:
        print(f"Checking for Python version {target_version}...")

    for instance in instances:
        if _version_key(instance)[: len(target_parts)] == target_parts:
            if verbose:
                print(f"Selected Python {instance.version} at {instance.executable}")
            return instance

    available = ", ".join(i.version for i in instances)
    raise RuntimeError(f"No Python {target_version} on the remote host. Available: {available}")


def get_any_python_instance(conn: Connection, verbose: bool = True) -> PythonInstance:
    """The newest python3 interpreter on the host."""
    instance = get_python_instances(conn, verbose=verbose)[0]
    if verbose:
        print(f"Selected Python {instance.version} at {instance.executable}")
    return instance
