"""Deploy Python apps to Linux servers over SSH, with plain functions on top of Fabric."""

__version__ = "1.0.1"

from .models import Host, Key, Option, Password, PythonInstance, SupervisorService, Venv
from .connection import connect, has_sudo_password, require_sudo
from .python import get_any_python_instance, get_python_instances, get_target_python_instance
from .venv import create_venv, delete_venv, run_in_venv
from .transfer import DEFAULT_IGNORE, upload_directory, upload_file
from .packages import (
    install_local_package,
    install_package_from_github,
    install_package_from_private_github,
    install_packages,
)
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
    "Host",
    "Password",
    "Key",
    "PythonInstance",
    "Venv",
    "SupervisorService",
    "Option",
    "connect",
    "has_sudo_password",
    "require_sudo",
    "get_python_instances",
    "get_target_python_instance",
    "get_any_python_instance",
    "create_venv",
    "delete_venv",
    "run_in_venv",
    "upload_file",
    "upload_directory",
    "DEFAULT_IGNORE",
    "install_packages",
    "install_local_package",
    "install_package_from_github",
    "install_package_from_private_github",
    "install_supervisor",
    "check_supervisor_installed",
    "create_supervisor_config",
    "deploy_supervisor_service",
    "supervisor_start",
    "supervisor_stop",
    "supervisor_restart",
    "supervisor_status",
]
