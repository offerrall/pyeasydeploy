"""Supervisord service management for pyeasydeploy.

Renders SupervisorService models into [program:x] config files,
deploys them to /etc/supervisor/conf.d and controls the services.

Every function that touches sudo calls require_sudo first: a missing
sudo password fails immediately with instructions instead of hanging.
"""

import io
import shlex
from typing import Any, Optional

from fabric import Connection

from .connection import require_sudo
from .models import SupervisorService


def install_supervisor(conn: Connection, verbose: bool = True) -> None:
    """Install supervisord via apt and enable it (Debian/Ubuntu).

    Idempotent: safe to run on a host that already has it.

    Args:
        conn: Connection to the remote host.
        verbose: Print progress (and apt output) to stdout.

    Raises:
        PermissionError: If no sudo password is configured (see
            connect_to_host).
    """
    require_sudo(conn, "install_supervisor")
    if verbose:
        print("Installing supervisor...")
    conn.sudo("apt-get update", hide=not verbose, warn=True)
    conn.sudo("DEBIAN_FRONTEND=noninteractive apt-get install -y supervisor",
              hide=not verbose)
    conn.sudo("systemctl enable supervisor", hide=True)
    conn.sudo("systemctl start supervisor", hide=True)
    if verbose:
        print("Supervisor installed and started")


def check_supervisor_installed(conn: Connection) -> bool:
    """Return True if supervisorctl is available on the remote host.

    Args:
        conn: Connection to the remote host.
    """
    return conn.run("which supervisorctl", warn=True, hide=True).ok


def _render_value(value: Any) -> str:
    """Render a config value: bools as supervisord's true/false."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def create_supervisor_config(service: SupervisorService) -> str:
    """Render a SupervisorService into [program:x] INI text.

    Named fields come first (None fields are omitted entirely, letting
    supervisord defaults apply), then every `extra` option verbatim.
    The model's own validation already guarantees nothing here can
    corrupt the INI structure.

    Args:
        service: The service description to render.

    Returns:
        The configuration file content, ending in a newline.
    """
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
    for key, value in service.extra.items():
        lines.append(f"{key}={_render_value(value)}")
    return "\n".join(lines) + "\n"


def deploy_supervisor_service(
    conn: Connection, service: SupervisorService, verbose: bool = True
) -> None:
    """Deploy a service config to /etc/supervisor/conf.d and load it.

    The config is rendered in memory and uploaded directly (no local
    temp file: nothing touches your working directory, concurrent
    deploys cannot collide). Existing config with the same name is
    replaced — destructive, like the rest of the library.

    Supervisord re-reads its configs; the service starts if
    autostart=True. Already-running services with changed config are
    restarted by 'supervisorctl update'.

    Args:
        conn: Connection to the remote host.
        service: The service description to deploy.
        verbose: Print progress to stdout.

    Raises:
        PermissionError: If no sudo password is configured (see
            connect_to_host).
    """
    require_sudo(conn, "deploy_supervisor_service")
    config_content = create_supervisor_config(service)

    # Unique remote temp file, then a sudo mv into place: conf.d is
    # root-owned, but SFTP runs as the SSH user, so we stage in /tmp.
    temp_remote = conn.run(
        "mktemp /tmp/pyeasydeploy.conf.XXXXXX", hide=True
    ).stdout.strip()

    try:
        if verbose:
            print(f"Uploading config for [program:{service.name}]")
        conn.put(io.StringIO(config_content), temp_remote)

        remote_config = f"/etc/supervisor/conf.d/{service.name}.conf"
        if verbose:
            print(f"Moving config to {remote_config}")
        conn.sudo("mkdir -p /etc/supervisor/conf.d", hide=True)
        conn.sudo(f"mv {shlex.quote(temp_remote)} {shlex.quote(remote_config)}",
                  hide=True)
        # mktemp creates mode 600 owned by the SSH user; make it
        # world-readable root-owned config like apt would.
        conn.sudo(f"chown root:root {shlex.quote(remote_config)}", hide=True)
        conn.sudo(f"chmod 644 {shlex.quote(remote_config)}", hide=True)

        if verbose:
            print("Reloading supervisor")
        conn.sudo("supervisorctl reread", hide=True)
        conn.sudo("supervisorctl update", hide=True)
    finally:
        # If anything above failed before the mv, don't leave the
        # staged file behind.
        conn.run(f"rm -f {shlex.quote(temp_remote)}", hide=True, warn=True)


def supervisor_start(conn: Connection, service_name: str, verbose: bool = True) -> Any:
    """Start a supervised service.

    Args:
        conn: Connection to the remote host.
        service_name: Name of the [program:x] entry.
        verbose: Print progress to stdout.

    Raises:
        PermissionError: If no sudo password is configured.
    """
    require_sudo(conn, "supervisor_start")
    if verbose:
        print(f"Starting: {service_name}")
    return conn.sudo(f"supervisorctl start {shlex.quote(service_name)}")


def supervisor_stop(conn: Connection, service_name: str, verbose: bool = True) -> Any:
    """Stop a supervised service.

    Args:
        conn: Connection to the remote host.
        service_name: Name of the [program:x] entry.
        verbose: Print progress to stdout.

    Raises:
        PermissionError: If no sudo password is configured.
    """
    require_sudo(conn, "supervisor_stop")
    if verbose:
        print(f"Stopping: {service_name}")
    return conn.sudo(f"supervisorctl stop {shlex.quote(service_name)}")


def supervisor_restart(conn: Connection, service_name: str, verbose: bool = True) -> Any:
    """Restart a supervised service.

    Args:
        conn: Connection to the remote host.
        service_name: Name of the [program:x] entry.
        verbose: Print progress to stdout.

    Raises:
        PermissionError: If no sudo password is configured.
    """
    require_sudo(conn, "supervisor_restart")
    if verbose:
        print(f"Restarting: {service_name}")
    return conn.sudo(f"supervisorctl restart {shlex.quote(service_name)}")


def supervisor_status(conn: Connection, service_name: Optional[str] = None) -> Any:
    """Show status of one service, or all of them.

    Args:
        conn: Connection to the remote host.
        service_name: Name of a [program:x] entry, or None for all.

    Raises:
        PermissionError: If no sudo password is configured.
    """
    require_sudo(conn, "supervisor_status")
    if service_name:
        return conn.sudo(f"supervisorctl status {shlex.quote(service_name)}")
    return conn.sudo("supervisorctl status")