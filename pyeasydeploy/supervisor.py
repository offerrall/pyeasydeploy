from fabric import Connection
from typing import NamedTuple
from pathlib import Path

from .transfer import upload_file

class SupervisorService(NamedTuple):
    name: str
    command: str
    directory: str
    user: str
    autostart: bool = True
    autorestart: bool = True
    stdout_logfile: str = "/var/log/supervisor/%(program_name)s.log"
    stderr_logfile: str = "/var/log/supervisor/%(program_name)s_err.log"

def install_supervisor(conn: Connection, verbose: bool = True):
    if verbose: print("Installing supervisor...")
    conn.sudo("apt-get update", hide=not verbose, warn=True)
    conn.sudo("apt-get install -y supervisor", hide=not verbose)
    conn.sudo("systemctl enable supervisor", hide=True)
    conn.sudo("systemctl start supervisor", hide=True)
    if verbose: print("Supervisor installed and started")

def check_supervisor_installed(conn: Connection) -> bool:
    result = conn.run("which supervisorctl", warn=True, hide=True)
    return result.ok

def create_supervisor_config(service: SupervisorService) -> str:
    autostart = "true" if service.autostart else "false"
    autorestart = "true" if service.autorestart else "false"
    
    config = f"""[program:{service.name}]
command={service.command}
directory={service.directory}
user={service.user}
autostart={autostart}
autorestart={autorestart}
stdout_logfile={service.stdout_logfile}
stderr_logfile={service.stderr_logfile}
"""
    return config

def deploy_supervisor_service(conn: Connection, service: SupervisorService, verbose: bool = True):
    config_content = create_supervisor_config(service)
    
    local_temp = Path.cwd() / f"{service.name}.conf"
    
    with open(local_temp, 'w') as f:
        f.write(config_content)
    
    try:
        temp_remote = f"/tmp/{service.name}.conf"
        upload_file(conn, str(local_temp), temp_remote, verbose=verbose)
        
        remote_config = f"/etc/supervisor/conf.d/{service.name}.conf"
        if verbose: print(f"Moving config to {remote_config}")
        
        conn.sudo(f"mkdir -p /etc/supervisor/conf.d", hide=True)
        conn.sudo(f"mv {temp_remote} {remote_config}", hide=True)
        
        if verbose: print(f"Reloading supervisor")
        conn.sudo("supervisorctl reread", hide=True)
        conn.sudo("supervisorctl update", hide=True)
    finally:
        local_temp.unlink()

def supervisor_start(conn: Connection, service_name: str, verbose: bool = True):
    if verbose: print(f"Starting: {service_name}")
    conn.sudo(f"supervisorctl start {service_name}")

def supervisor_stop(conn: Connection, service_name: str, verbose: bool = True):
    if verbose: print(f"Stopping: {service_name}")
    conn.sudo(f"supervisorctl stop {service_name}")

def supervisor_restart(conn: Connection, service_name: str, verbose: bool = True):
    if verbose: print(f"Restarting: {service_name}")
    conn.sudo(f"supervisorctl restart {service_name}")

def supervisor_status(conn: Connection, service_name: str = None):
    if service_name:
        return conn.sudo(f"supervisorctl status {service_name}")
    return conn.sudo("supervisorctl status")