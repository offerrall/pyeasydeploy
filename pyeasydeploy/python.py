import posixpath
import shlex

from .connection import fabric_connection
from .models import Python, Uv


def uv_command(uv: Uv, args: str) -> str:
    base = posixpath.dirname(posixpath.dirname(uv.path))
    env = (f"UV_PYTHON_INSTALL_DIR={shlex.quote(base + '/python')} "
           f"UV_CACHE_DIR={shlex.quote(base + '/cache')} UV_PROJECT_ENVIRONMENT=.venv")
    return f"{env} {shlex.quote(uv.path)} {args}"


def ensure_python(uv: Uv, version: str) -> Python:
    upgrade = "--upgrade " if version.count(".") == 1 else ""
    quoted = shlex.quote(version)
    output = fabric_connection(uv.server).run(
        f"{uv_command(uv, f'python install {upgrade}--no-bin {quoted}')} && "
        f"path=$({uv_command(uv, f'python find --system --no-project --managed-python {quoted}')}) && "
        "echo \"$path\" && \"$path\" -c 'import platform; print(platform.python_version())'",
        hide=True).stdout
    path, full_version = output.strip().splitlines()[-2:]
    return Python(uv=uv, version=full_version, path=path)
