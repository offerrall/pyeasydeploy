"""Remote Python interpreter discovery for pyeasydeploy.

Finds python3.X interpreters on the remote host and returns them as
validated PythonInstance models. Only real interpreters are matched:
companion binaries like python3.11-config are filtered out.
"""

import re
from typing import List

from fabric import Connection

from .models import PythonInstance

# Matches real interpreter paths only: .../python3 or .../python3.11,
# never python3.11-config, python3-qt or other companions.
_INTERPRETER_RE = re.compile(r"^/usr/bin/python3(\.\d+)?$")


def _version_key(instance: PythonInstance) -> tuple:
    """Sort key: numeric version components, newest-first friendly."""
    return tuple(int(part) for part in instance.version.split("."))


def get_python_instances(conn: Connection, verbose: bool = True) -> List[PythonInstance]:
    """Discover python3 interpreters installed in /usr/bin on the host.

    Companion binaries (python3.11-config and similar) are excluded.
    Results are sorted newest version first.

    Args:
        conn: Connection to the remote host.
        verbose: Print discovery progress to stdout.

    Returns:
        Non-empty list of PythonInstance, newest version first.

    Raises:
        RuntimeError: If no python3 interpreter is found on the host.
    """
    if verbose:
        print("Searching for Python instances...")

    # 2>/dev/null + warn=True: an empty glob must NOT raise a Fabric
    # error here — "nothing found" is our RuntimeError below, with a
    # message that actually explains the situation.
    result = conn.run("ls -1 /usr/bin/python3* 2>/dev/null", hide=True, warn=True)

    instances = []
    for line in result.stdout.splitlines():
        path = line.strip()
        if not _INTERPRETER_RE.match(path):
            continue
        version = path.rsplit("/", 1)[-1].removeprefix("python")
        if not version[0].isdigit():
            continue  # defensive; the regex already guarantees this
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
    """Find an interpreter matching a version, by components.

    Matching is component-wise, so "3.1" matches only Python 3.1 —
    NOT 3.11 or 3.10 (a plain startswith would). "3" matches any
    python3.X; if several match, the newest wins.

    Args:
        conn: Connection to the remote host.
        target_version: Version to look for, e.g. "3.11" or "3".
        verbose: Print discovery progress to stdout.

    Returns:
        The newest PythonInstance whose version starts with the given
        components.

    Raises:
        TypeError: If target_version is not a str.
        ValueError: If target_version is empty or not dot-separated
            integers.
        RuntimeError: If no interpreter is found, or none matches.
    """
    if not isinstance(target_version, str):
        raise TypeError(
            f"target_version must be str, got {type(target_version).__name__}"
        )
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

    for instance in instances:  # already newest-first
        parts = _version_key(instance)
        if parts[: len(target_parts)] == target_parts:
            if verbose:
                print(f"Selected Python {instance.version} at {instance.executable}")
            return instance

    available = ", ".join(i.version for i in instances)
    raise RuntimeError(
        f"No Python {target_version} on the remote host. "
        f"Available: {available}"
    )


def get_any_python_instance(conn: Connection, verbose: bool = True) -> PythonInstance:
    """Return the newest python3 interpreter available on the host.

    Args:
        conn: Connection to the remote host.
        verbose: Print discovery progress to stdout.

    Returns:
        The newest PythonInstance found.

    Raises:
        RuntimeError: If no python3 interpreter is found on the host.
    """
    instance = get_python_instances(conn, verbose=verbose)[0]
    if verbose:
        print(f"Selected Python {instance.version} at {instance.executable}")
    return instance