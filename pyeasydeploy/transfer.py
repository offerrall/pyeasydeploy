"""File and directory upload for pyeasydeploy.

Uploads local files/trees to the remote host over SFTP, with ignore
patterns.

PHILOSOPHY — DESTRUCTIVE, ALWAYS: the remote destination is removed
before uploading, every time. What ends up on the server is exactly
what you have locally — no drift, no orphan files from previous
deploys, no merge semantics. The only protection is structural: a
short deny-list of system roots that can never be a deploy
destination (a typo there would be catastrophic and is never
legitimate).
"""

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
"""Glob patterns excluded from upload_directory by default."""

# Destinations that are never legitimate deploy targets. Removing them
# would destroy the system; a path matching this list is always a typo.
_FORBIDDEN_DESTINATIONS = frozenset(
    {"/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/opt",
     "/proc", "/root", "/run", "/sbin", "/srv", "/sys", "/tmp",
     "/usr", "/var"}
)


def _check_destination(remote_path: str) -> str:
    """Reject remote destinations that would wipe a system root.

    Raises:
        TypeError: If remote_path is not a str.
        ValueError: If remote_path is empty, not absolute, or is (or
            normalizes to) a protected system root.
    """
    if not isinstance(remote_path, str):
        raise TypeError(
            f"remote path must be str, got {type(remote_path).__name__}"
        )
    if not remote_path.strip():
        raise ValueError("remote path must be a non-empty string")
    normalized = str(PurePosixPath(remote_path))
    if not normalized.startswith("/"):
        raise ValueError(
            f"remote path must be absolute, got {remote_path!r}"
        )
    if normalized in _FORBIDDEN_DESTINATIONS:
        raise ValueError(
            f"Refusing {remote_path!r} as deploy destination: it is a "
            "system root and uploads are destructive (the destination "
            "is removed first). Use a subdirectory instead."
        )
    return normalized


def upload_file(
    conn: Connection,
    local_file: str,
    remote_file: str,
    verbose: bool = True,
) -> None:
    """Upload a single file to the remote host.

    DESTRUCTIVE: any existing file (or directory) at remote_file is
    removed first. Parent directories are created as needed.

    Args:
        conn: Connection to the remote host.
        local_file: Path to the local file.
        remote_file: Absolute remote destination path.
        verbose: Print progress to stdout.

    Raises:
        TypeError / ValueError: If remote_file is not an absolute path
            or is a protected system root.
        FileNotFoundError: If local_file does not exist or is not a
            file.
    """
    remote_file = _check_destination(remote_file)
    local_path = Path(local_file)
    if not local_path.is_file():
        raise FileNotFoundError(f"Local file not found: {local_file}")

    conn.run(f"rm -rf {shlex.quote(remote_file)}", hide=True, warn=True)

    remote_dir = str(PurePosixPath(remote_file).parent)
    conn.run(f"mkdir -p {shlex.quote(remote_dir)}", hide=True)

    if verbose:
        print(f"Uploading {local_file} to {remote_file}")
    conn.put(str(local_path), remote_file)
    if verbose:
        print("Upload complete")


def upload_directory(
    conn: Connection,
    local_dir: str,
    remote_dir: str,
    ignore: Optional[List[str]] = None,
    verbose: bool = True,
) -> None:
    """Upload a local directory tree to the remote host.

    DESTRUCTIVE: the existing remote_dir is removed entirely first.
    After this call, the remote tree is exactly the local tree (minus
    ignored patterns) — no drift, no leftovers from previous deploys.

    Args:
        conn: Connection to the remote host.
        local_dir: Path to the local directory.
        remote_dir: Absolute remote destination path.
        ignore: Glob patterns to exclude (matched against file and
            directory names, not paths). None uses DEFAULT_IGNORE;
            pass [] to upload everything.
        verbose: Print progress to stdout.

    Raises:
        TypeError / ValueError: If remote_dir is not an absolute path
            or is a protected system root.
        FileNotFoundError: If local_dir does not exist or is not a
            directory.
    """
    remote_dir = _check_destination(remote_dir)
    local_path = Path(local_dir)
    if not local_path.is_dir():
        raise FileNotFoundError(f"Local directory not found: {local_dir}")

    patterns = DEFAULT_IGNORE if ignore is None else ignore

    conn.run(f"rm -rf {shlex.quote(remote_dir)}", hide=True, warn=True)

    if verbose:
        print(f"Uploading {local_dir} to {remote_dir}")

    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [
            d for d in dirs
            if not any(fnmatch.fnmatch(d, pat) for pat in patterns)
        ]

        relative_root = Path(root).relative_to(local_path)
        # PurePosixPath join: correct remote separators even from Windows.
        remote_root = str(PurePosixPath(remote_dir) / PurePosixPath(*relative_root.parts))

        # One mkdir -p per tree level: fewer SSH round-trips than one
        # call per directory.
        to_create = [str(PurePosixPath(remote_root) / d) for d in dirs]
        if relative_root == Path("."):
            to_create.append(remote_root)  # ensure the root itself exists
        if to_create:
            quoted = " ".join(shlex.quote(p) for p in to_create)
            conn.run(f"mkdir -p {quoted}", hide=True)

        for file_name in files:
            if any(fnmatch.fnmatch(file_name, pat) for pat in patterns):
                continue
            local_file = Path(root) / file_name
            remote_file = str(PurePosixPath(remote_root) / file_name)
            conn.put(str(local_file), remote_file)

    if verbose:
        print("Upload complete")