"""Uploads over SFTP. Destructive, always: the destination is removed first, so the server
ends up with exactly the local files, with nothing left over from earlier deploys."""

import fnmatch
import os
import shlex
from pathlib import Path, PurePosixPath
from typing import List, Optional

from fabric import Connection

DEFAULT_IGNORE: List[str] = [
    ".git", ".venv", "venv", "__pycache__", ".vscode", ".idea",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "*.pyc", "*.pyo", "*.db", "*.sqlite", "*.sqlite3", ".DS_Store",
]
"""Name patterns upload_directory skips by default."""

# Never a legitimate destination: removing one would destroy the system.
_FORBIDDEN_DESTINATIONS = frozenset({
    "/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/opt", "/proc",
    "/root", "/run", "/sbin", "/srv", "/sys", "/tmp", "/usr", "/var",
})


def check_destination(remote_path: str) -> str:
    """The normalized remote_path, or ValueError if removing it would wipe a system root.

    Every destructive operation starts with an `rm -rf` on its path, so each calls this first.
    """
    if not isinstance(remote_path, str):
        raise TypeError(f"remote path must be str, got {type(remote_path).__name__}")
    if not remote_path.strip():
        raise ValueError("remote path must be a non-empty string")
    normalized = str(PurePosixPath(remote_path))
    if not normalized.startswith("/"):
        raise ValueError(f"remote path must be absolute, got {remote_path!r}")
    if normalized in _FORBIDDEN_DESTINATIONS:
        raise ValueError(
            f"Refusing {remote_path!r} as destination: it is a system "
            "root and this operation is destructive (the path is "
            "removed first). Use a subdirectory instead."
        )
    return normalized


def _check_mode(mode: int) -> int:
    # bool is an int: True would silently become mode 1.
    if not isinstance(mode, int) or isinstance(mode, bool):
        raise TypeError(f"mode must be int, got {type(mode).__name__}")
    if not 0 <= mode <= 0o7777:
        raise ValueError(
            f"mode must be a permission bitmask between 0 and 0o7777, "
            f"got {mode!r} (octal {mode:o}). Write it in octal: 0o644."
        )
    return mode


def upload_file(
    conn: Connection,
    local_file: str,
    remote_file: str,
    verbose: bool = True,
    mode: Optional[int] = None,
) -> None:
    """Upload one file, replacing whatever is at remote_file and creating its parents.

    Without mode (e.g. 0o600), permissions depend on the machine you deploy from.
    """
    remote_file = check_destination(remote_file)
    if mode is not None:
        _check_mode(mode)
    local_path = Path(local_file)
    if not local_path.is_file():
        raise FileNotFoundError(f"Local file not found: {local_file}")

    conn.run(f"rm -rf {shlex.quote(remote_file)}", hide=True, warn=True)
    conn.run(f"mkdir -p {shlex.quote(str(PurePosixPath(remote_file).parent))}", hide=True)

    if verbose:
        print(f"Uploading {local_file} to {remote_file}")
    conn.put(str(local_path), remote_file)
    if mode is not None:
        conn.run(f"chmod {mode:o} {shlex.quote(remote_file)}", hide=True)
    if verbose:
        print("Upload complete")


def upload_directory(
    conn: Connection,
    local_dir: str,
    remote_dir: str,
    ignore: Optional[List[str]] = None,
    verbose: bool = True,
    mode: Optional[int] = None,
) -> None:
    """Replace remote_dir with a copy of local_dir.

    ignore holds name patterns (not paths); None means DEFAULT_IGNORE, [] uploads
    everything. mode applies to every file; directories keep the remote umask.
    """
    remote_dir = check_destination(remote_dir)
    if mode is not None:
        _check_mode(mode)
    local_path = Path(local_dir)
    if not local_path.is_dir():
        raise FileNotFoundError(f"Local directory not found: {local_dir}")

    patterns = DEFAULT_IGNORE if ignore is None else ignore

    conn.run(f"rm -rf {shlex.quote(remote_dir)}", hide=True, warn=True)

    if verbose:
        print(f"Uploading {local_dir} to {remote_dir}")

    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pat) for pat in patterns)]

        relative_root = Path(root).relative_to(local_path)
        # PurePosixPath: remote separators stay "/" when deploying from Windows.
        remote_root = str(PurePosixPath(remote_dir) / PurePosixPath(*relative_root.parts))

        # One mkdir per level of the tree, not per directory: fewer SSH round trips.
        to_create = [str(PurePosixPath(remote_root) / d) for d in dirs]
        if relative_root == Path("."):
            to_create.append(remote_root)
        if to_create:
            conn.run(f"mkdir -p {' '.join(shlex.quote(p) for p in to_create)}", hide=True)

        for file_name in files:
            if any(fnmatch.fnmatch(file_name, pat) for pat in patterns):
                continue
            conn.put(str(Path(root) / file_name), str(PurePosixPath(remote_root) / file_name))

    if mode is not None:
        conn.run(f"find {shlex.quote(remote_dir)} -type f -exec chmod {mode:o} {{}} +", hide=True)

    if verbose:
        print("Upload complete")
