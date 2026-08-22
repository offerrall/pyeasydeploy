"""pyeasydeploy — deploy Python apps to Linux servers over SSH.

No agents, no YAML, no magic: plain Python functions that do exactly
what they say. See the README for the philosophy (destructive and
reproducible uploads and venvs, fail-fast validation, trust in the
user) and for what falls outside that guarantee.

Typical flow::

    from pyeasydeploy import (
        connect_to_host, get_target_python_instance, create_venv,
        install_local_package, deploy_supervisor_service,
        SupervisorService,
    )

    conn = connect_to_host(host, user, key_filename="~/.ssh/id_ed25519",
                           sudo_password="...")
    py = get_target_python_instance(conn, "3.11")
    venv = create_venv(conn, py, "/home/deploy/venvs/myapp")
    install_local_package(conn, venv, "./myapp")
    deploy_supervisor_service(conn, SupervisorService(
        name="myapp",
        command="/home/deploy/venvs/myapp/bin/python -m myapp",
    ))
"""

__version__ = "0.1.6"

# Models (foundation layer; importable standalone)
from .models import PythonInstance, SupervisorService, VenvPython

# Connection
from .connection import connect_to_host, has_sudo_password, require_sudo

# Remote Python discovery
from .python import (
    get_any_python_instance,
    get_python_instances,
    get_target_python_instance,
)

# Virtual environments
from .venv import create_venv, delete_venv, run_in_venv

# File transfer
from .transfer import DEFAULT_IGNORE, upload_directory, upload_file

# Package installation
from .packages import (
    install_local_package,
    install_package_from_github,
    install_package_from_private_github,
    install_packages,
)

# Supervisor services
from .supervisor import (
    check_supervisor_installed,
    create_supervisor_config,
    deploy_supervisor_service,
    install_supervisor,
    supervisor_restart,
    supervisor_start,
    supervisor_status,
    supervisor_stop,
)

__all__ = [
    "__version__",
    # models
    "PythonInstance",
    "VenvPython",
    "SupervisorService",
    # connection
    "connect_to_host",
    "has_sudo_password",
    "require_sudo",
    # python
    "get_python_instances",
    "get_target_python_instance",
    "get_any_python_instance",
    # venv
    "create_venv",
    "delete_venv",
    "run_in_venv",
    # transfer
    "upload_file",
    "upload_directory",
    "DEFAULT_IGNORE",
    # packages
    "install_packages",
    "install_local_package",
    "install_package_from_github",
    "install_package_from_private_github",
    # supervisor
    "install_supervisor",
    "check_supervisor_installed",
    "create_supervisor_config",
    "deploy_supervisor_service",
    "supervisor_start",
    "supervisor_stop",
    "supervisor_restart",
    "supervisor_status",
]
