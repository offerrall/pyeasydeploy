import fnmatch
import io
import posixpath
import re
import shlex
import tarfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from .connection import fabric_connection
from .models import NAME, App, Python, Release, Server
from .paths import inside, remove
from .python import uv_command
from .server import pyeasydeploy_dir

IGNORE = (".git", ".venv", "venv", "__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache",
          ".ruff_cache", "node_modules", ".DS_Store", "*.db", "*.sqlite", "*.sqlite3")


def app_dir(server: Server, name: str) -> str:
    return inside(pyeasydeploy_dir(server), f"{pyeasydeploy_dir(server)}/apps/{name}")


def service_name(name: str) -> str:
    if not re.fullmatch(NAME, name):
        raise ValueError(f"Invalid app name {name!r}: must be letters, digits, '_', '.' or '-'")
    return f"pyeasydeploy-{name}.service"


def _quoted(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")


def service_unit(app: App, directory: str) -> str:
    current = f"{directory}/current"
    command = app.command.replace("%", "%%")
    environment = "".join(f'Environment="{name}={_quoted(value)}"\n' for name, value in app.environment)
    return (
        "[Unit]\n"
        f"Description=pyeasydeploy {app.name}\n"
        "\n"
        "[Service]\n"
        "Type=exec\n"
        f"WorkingDirectory={current}\n"
        f"ExecStart={current}/.venv/bin/{command}\n"
        "Environment=PYTHONUNBUFFERED=1\n"
        f"{environment}"
        "Restart=always\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def _keep(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    name = info.name.rsplit("/", 1)[-1]
    return None if any(fnmatch.fnmatch(name, pattern) for pattern in IGNORE) else info


def _locked_paths(source: Path) -> list[str]:
    lock = tomllib.loads((source / "uv.lock").read_text())
    paths = {"pyproject.toml", "uv.lock"}
    for package in lock.get("package", []):
        for kind, path in package.get("source", {}).items():
            path = posixpath.normpath(path)
            if kind in ("editable", "directory", "path") or (kind == "virtual" and path != "."):
                paths.add(path)
    if "." in paths:
        return ["."]
    for path in paths:
        if not (source / path).resolve().is_relative_to(source.resolve()):
            raise ValueError(f"{source / 'uv.lock'} points outside {source}: {path}")
    return sorted(paths)


def _tarball(source: Path, package: str | None = None) -> bytes:
    source = source.expanduser().resolve()
    if not (source / "uv.lock").is_file():
        raise FileNotFoundError(f"{source} has no uv.lock: run 'uv lock' there first")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path in _locked_paths(source) if package else ["."]:
            tar.add(source / path, arcname=path, filter=_keep)
    return buffer.getvalue()


def _systemctl(server: Server, *args: str, warn: bool = False) -> str:
    calls = " && ".join(f"systemctl --user {arg}" for arg in args)
    command = f'export XDG_RUNTIME_DIR="/run/user/$(id -u)"; {calls}'
    return fabric_connection(server).run(command, hide=True, warn=warn).stdout.strip()


def _journal(server: Server, args: str) -> str:
    command = f'export XDG_RUNTIME_DIR="/run/user/$(id -u)"; journalctl --user --no-pager {args}'
    return fabric_connection(server).run(command, hide=True, warn=True).stdout


def _require_linger(server: Server) -> None:
    linger = fabric_connection(server).run('loginctl show-user "$(id -un)" -p Linger --value',
                                           hide=True, warn=True).stdout.strip()
    if linger != "yes":
        raise RuntimeError(f"Run this once as root on the server: loginctl enable-linger {server.user}")


def _build_release(python: Python, app: App) -> Release:
    server = python.uv.server
    conn = fabric_connection(server)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    release = Release(python=python, app=app, path=f"{app_dir(server, app.name)}/releases/{stamp}")
    path = shlex.quote(release.path)
    tarball = shlex.quote(f"{release.path}.tar.gz")

    data = _tarball(Path(app.source), app.package)

    conn.run(f"mkdir -p {path}", hide=True)
    try:
        conn.put(io.BytesIO(data), f"{release.path}.tar.gz")
        package = f" --package {shlex.quote(app.package)}" if app.package else ""
        sync = uv_command(python.uv, f"sync --directory {path} --frozen --no-dev --no-editable "
                                     f"--python {shlex.quote(python.path)}{package}")
        conn.run(f"tar xzf {tarball} -C {path} && rm {tarball} && {sync}", hide=True)
    except BaseException:
        remove(server, release.path, f"{release.path}.tar.gz")
        raise
    return release


def _activate_release(release: Release) -> None:
    server = release.python.uv.server
    conn = fabric_connection(server)
    directory = app_dir(server, release.app.name)
    unit = f"{directory}/{service_name(release.app.name)}"

    conn.put(io.StringIO(service_unit(release.app, directory)), unit)
    conn.run(f"chmod 600 {shlex.quote(unit)} && "
             f"ln -sfn {shlex.quote(release.path)} {shlex.quote(directory + '/current')}", hide=True)
    _systemctl(server, f"enable {shlex.quote(unit)}", "daemon-reload",
               f"restart {service_name(release.app.name)}")

    releases = conn.run(f"ls -1 {shlex.quote(directory + '/releases')}", hide=True).stdout.split()
    old = [f"{directory}/releases/{name}" for name in sorted(releases)[:-2]]
    remove(server, *(path for path in old if path != release.path))


def deploy_app(python: Python, app: App) -> Release:
    _require_linger(python.uv.server)
    release = _build_release(python, app)
    _activate_release(release)
    return release


def app_status(server: Server, name: str) -> str:
    return _systemctl(server, f"status --no-pager {service_name(name)}", warn=True)


def app_logs(server: Server, name: str, lines: int = 100) -> str:
    return _journal(server, f"-u {service_name(name)} -n {int(lines)}")


def restart_app(server: Server, name: str) -> None:
    _systemctl(server, f"restart {service_name(name)}")


def stop_app(server: Server, name: str) -> None:
    _systemctl(server, f"stop {service_name(name)}")
