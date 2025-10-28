# pyeasydeploy

Simple and replicable Python server deployment toolkit. Deploy your Python applications to remote servers with just a few lines of code.

> ⚠️ **Warning**: This library is in very early stages and currently in testing phase. Use at your own risk in production environments. APIs may change without notice.

## Features

- **Simple API** - Deploy servers with minimal configuration
- **Python Version Management** - Automatically detect and use specific Python versions
- **Multiple Package Sources** - Install from PyPI, local directories, or GitHub
- **Virtual Environment Management** - Automatic venv creation and activation
- **Supervisor Integration** - Service management with supervisord
- **SSH-based** - Secure remote deployment via SSH/Fabric
- **Cross-platform** - Works on Windows, Linux, and macOS

## Installation

```bash
pip install git+https://github.com/offerrall/pyeasydeploy.git
```

## Quick Start

```python
from pyeasydeploy import *

# Connect to remote server
connection = connect_to_host(
    host="192.168.1.130",
    user="myuser",
    password="mypassword",
    port=22  # optional, defaults to 22
)

# Setup Python environment
python_instance = get_target_python_instance(connection, "3.14")
venv_python = create_venv(connection, python_instance, "/home/myuser/venv")

# Install dependencies
install_packages(connection, venv_python, ["fastapi", "uvicorn[standard]"])

# Upload application code
upload_directory(connection, "./my_app", "/home/myuser/my_app")

# Configure supervisor service
service = SupervisorService(
    name="my_app",
    command=f"{venv_python.venv_path}/bin/uvicorn main:app --host 0.0.0.0 --port 8000",
    directory="/home/myuser/my_app",
    user="myuser"
)

# Deploy and start
if not check_supervisor_installed(connection):
    install_supervisor(connection)

deploy_supervisor_service(connection, service)
supervisor_start(connection, "my_app")
```

## Core Components

### Connection Management

```python
# Create connection to remote host
connection = connect_to_host(
    host="192.168.1.130",
    user="myuser",
    password="mypassword",
    port=22  # optional, defaults to 22
)
```

### Python Version Management

```python
# Get available Python versions
instances = get_python_instances(connection)

# Get specific Python version
python_instance = get_target_python_instance(connection, "3.14")
```

### Virtual Environment

```python
# Create virtual environment
venv_python = create_venv(connection, python_instance, "/home/myuser/venv")

# Run commands in venv
run_in_venv(connection, venv_python, "pip list")
```

### Package Installation

```python
# Install from PyPI
install_packages(connection, venv_python, ["fastapi==0.120.1", "uvicorn[standard]"])

# Install local package
install_local_package(connection, venv_python, "./my_package")

# Install from GitHub
install_package_from_github(connection, venv_python, "https://github.com/user/repo")
```

### File Transfer

```python
# Upload single file
upload_file(connection, "./config.json", "/home/myuser/app/config.json")

# Upload entire directory
upload_directory(connection, "./my_app", "/home/myuser/my_app")
```

### Supervisor Service Management

```python
# Install supervisor
install_supervisor(connection)

# Check if supervisor is installed
if check_supervisor_installed(connection):
    print("Supervisor is ready")

# Create service configuration
service = SupervisorService(
    name="my_service",
    command="/path/to/command",
    directory="/working/directory",
    user="myuser",
    autostart=True,
    autorestart=True
)

# Deploy service
deploy_supervisor_service(connection, service)

# Manage service
supervisor_start(connection, "my_service")
supervisor_stop(connection, "my_service")
supervisor_restart(connection, "my_service")
supervisor_status(connection, "my_service")
```

## Complete Example: FastAPI Deployment

```python
from pyeasydeploy import *

# Configuration
HOST = "192.168.1.130"
USER = "myuser"
PASSWORD = "mypassword"
PYTHON_VERSION = "3.14"
APP_NAME = "fastapi_app"
LOCAL_APP = "./my_fastapi_app"
REMOTE_APP = f"/home/{USER}/{APP_NAME}"

# Connect
connection = connect_to_host(host=HOST, user=USER, password=PASSWORD)

# Setup Python environment
python_instance = get_target_python_instance(connection, PYTHON_VERSION)
venv_python = create_venv(connection, python_instance, f"/home/{USER}/venv")

# Install dependencies
install_packages(connection, venv_python, [
    "fastapi==0.120.1",
    "uvicorn[standard]",
    "pydantic",
    "python-dotenv"
])

# Upload application
upload_directory(connection, LOCAL_APP, REMOTE_APP)

# Setup supervisor
if not check_supervisor_installed(connection):
    install_supervisor(connection)

service = SupervisorService(
    name=APP_NAME,
    command=f"{venv_python.venv_path}/bin/uvicorn main:app --host 0.0.0.0 --port 8000",
    directory=REMOTE_APP,
    user=USER
)

deploy_supervisor_service(connection, service)
supervisor_start(connection, APP_NAME)

# Verify deployment
print("\n✅ Deployment successful!")
print(f"🌐 Access at: http://{HOST}:8000")
supervisor_status(connection, APP_NAME)
```

## Requirements

- Python 3.8+
- fabric
- paramiko

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details