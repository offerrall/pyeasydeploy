"""supervisord services on Arch and Debian-based hosts, detected from /etc/os-release.

Every function that needs sudo calls require_sudo first, so a missing password fails at
once instead of hanging.
"""

import io
import shlex
from dataclasses import dataclass
from typing import Any, Optional

from fabric import Connection

from .connection import require_sudo
from .models import SupervisorService


@dataclass(frozen=True)
class _SupervisorPlatform:
    install_commands: tuple[str, ...]
    service: str
    config_directory: str
    config_extension: str


_DEBIAN = _SupervisorPlatform(
    install_commands=(
        "apt-get update",
        "DEBIAN_FRONTEND=noninteractive apt-get install -y supervisor",
    ),
    service="supervisor.service",
    config_directory="/etc/supervisor/conf.d",
    config_extension=".conf",
)

_ARCH = _SupervisorPlatform(
    install_commands=("pacman -S --needed --noconfirm supervisor",),
    service="supervisord.service",
    config_directory="/etc/supervisor.d",
    config_extension=".ini",
)


def _supervisor_platform(conn: Connection) -> _SupervisorPlatform:
    release = {}
    for line in conn.run("cat /etc/os-release", hide=True).stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            release[key] = value.strip().strip('"\'')

    distribution = release.get("ID", "").lower()
    family = release.get("ID_LIKE", "").lower().split()
    if distribution == "arch" or "arch" in family:
        return _ARCH
    if distribution in {"debian", "ubuntu"} or "debian" in family:
        return _DEBIAN
    raise RuntimeError(
        f"Unsupported remote Linux distribution for Supervisor: {distribution or 'unknown'}"
    )


def install_supervisor(conn: Connection, verbose: bool = True) -> None:
    """Install, enable and start supervisord. Safe to run again."""
    require_sudo(conn, "install_supervisor")
    platform = _supervisor_platform(conn)
    if verbose:
        print("Installing supervisor...")
    for command in platform.install_commands:
        conn.sudo(command, hide=not verbose)
    conn.sudo(f"systemctl enable {platform.service}", hide=True)
    conn.sudo(f"systemctl start {platform.service}", hide=True)
    if verbose:
        print("Supervisor installed and started")


def check_supervisor_installed(conn: Connection) -> bool:
    return conn.run("which supervisorctl", warn=True, hide=True).ok


def _render_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def create_supervisor_config(service: SupervisorService) -> str:
    """The [program:name] INI text: the named fields that are not None, then `extra` in order."""
    lines = [f"[program:{service.name}]"]
    named = [
        ("command", service.command),
        ("directory", service.directory),
        ("user", service.user),
        ("autostart", service.autostart),
        ("autorestart", service.autorestart),
        ("stdout_logfile", service.stdout_logfile),
        ("stderr_logfile", service.stderr_logfile),
        ("environment", service.environment),
    ]
    for key, value in named:
        if value is not None:
            lines.append(f"{key}={_render_value(value)}")
    for option in service.extra:
        lines.append(f"{option.key}={_render_value(option.value)}")
    return "\n".join(lines) + "\n"


def deploy_supervisor_service(
    conn: Connection, service: SupervisorService, verbose: bool = True
) -> None:
    """Write the service's config, replacing any with the same name, and reload supervisord.

    It starts if autostart is set; a running service whose config changed is restarted.
    """
    require_sudo(conn, "deploy_supervisor_service")
    platform = _supervisor_platform(conn)
    config_content = create_supervisor_config(service)

    # SFTP runs as the SSH user and the config directory is root's: stage in /tmp, then sudo mv.
    temp_remote = conn.run("mktemp /tmp/pyeasydeploy.conf.XXXXXX", hide=True).stdout.strip()
    try:
        if verbose:
            print(f"Uploading config for [program:{service.name}]")
        conn.put(io.StringIO(config_content), temp_remote)

        remote_config = f"{platform.config_directory}/{service.name}{platform.config_extension}"
        if verbose:
            print(f"Moving config to {remote_config}")
        conn.sudo(f"mkdir -p {platform.config_directory}", hide=True)
        conn.sudo(f"mv {shlex.quote(temp_remote)} {shlex.quote(remote_config)}", hide=True)
        # mktemp leaves it 600 and owned by the SSH user.
        conn.sudo(f"chown root:root {shlex.quote(remote_config)}", hide=True)
        conn.sudo(f"chmod 644 {shlex.quote(remote_config)}", hide=True)

        if verbose:
            print("Reloading supervisor")
        conn.sudo("supervisorctl reread", hide=True)
        conn.sudo("supervisorctl update", hide=True)
    finally:
        conn.run(f"rm -f {shlex.quote(temp_remote)}", hide=True, warn=True)


def supervisor_start(conn: Connection, service_name: str, verbose: bool = True) -> Any:
    require_sudo(conn, "supervisor_start")
    if verbose:
        print(f"Starting: {service_name}")
    return conn.sudo(f"supervisorctl start {shlex.quote(service_name)}")


def supervisor_stop(conn: Connection, service_name: str, verbose: bool = True) -> Any:
    require_sudo(conn, "supervisor_stop")
    if verbose:
        print(f"Stopping: {service_name}")
    return conn.sudo(f"supervisorctl stop {shlex.quote(service_name)}")


def supervisor_restart(conn: Connection, service_name: str, verbose: bool = True) -> Any:
    require_sudo(conn, "supervisor_restart")
    if verbose:
        print(f"Restarting: {service_name}")
    return conn.sudo(f"supervisorctl restart {shlex.quote(service_name)}")


def supervisor_status(conn: Connection, service_name: Optional[str] = None) -> Any:
    """The status of one service, or of all of them when service_name is None."""
    require_sudo(conn, "supervisor_status")
    if service_name:
        return conn.sudo(f"supervisorctl status {shlex.quote(service_name)}")
    return conn.sudo("supervisorctl status")
