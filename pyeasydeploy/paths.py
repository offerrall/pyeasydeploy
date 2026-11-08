import posixpath
import shlex

from .connection import fabric_connection
from .models import Server
from .server import pyeasydeploy_dir


def inside(base: str, path: str) -> str:
    normalized = posixpath.normpath(path)
    if normalized != path.rstrip("/") or not normalized.startswith(base + "/"):
        raise ValueError(f"Refusing {path!r}: pyeasydeploy only touches paths inside {base}")
    return normalized


def remove_command(base: str, *paths: str) -> str:
    quoted = " ".join(shlex.quote(inside(base, path)) for path in paths)
    return (f"base=$(cd {shlex.quote(base)} && pwd -P) || exit 0; "
            f"for path in {quoted}; do "
            'parent=$(cd "$(dirname "$path")" 2>/dev/null && pwd -P) || continue; '
            'case "$parent/" in "$base"/*) ;; '
            '*) echo "Refusing $path: it resolves outside $base" >&2; exit 1;; esac; '
            f"done; rm -rf {quoted}")


def remove(server: Server, *paths: str) -> None:
    if paths:
        fabric_connection(server).run(remove_command(pyeasydeploy_dir(server), *paths), hide=True)
