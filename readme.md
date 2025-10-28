# pyeasydeploy

Simple Python server deployment toolkit. Deploy to remote servers with just a few lines of code.

> ⚠️ **Warning**: Early stage library in testing phase. Use at your own risk. APIs may change.

## Why?

Tired of SSHing manually but Kubernetes is overkill for your $5 VPS? This is for you.

- **250 lines of code** - Read and understand it in minutes
- **Simple API** - If you can write Python, you can deploy
- **Built on Fabric** - Mix with pure Fabric commands anytime

## Installation

```bash
pip install git+https://github.com/offerrall/pyeasydeploy.git
```

## Quick Start

```python
from pyeasydeploy import *

# Connect (password or SSH key)
connection = connect_to_host(
    host="192.168.1.100",
    user="deploy",
    key_filename="~/.ssh/id_rsa"  # or password="..." for testing
)

# Setup environment
python = get_target_python_instance(connection, "3.11")
venv = create_venv(connection, python, "/home/deploy/venv")
install_packages(connection, venv, ["fastapi", "uvicorn[standard]"])

# Deploy app
upload_directory(connection, "./my_app", "/home/deploy/my_app")

# Run with supervisor
service = SupervisorService(
    name="my_app",
    command=f"{venv.venv_path}/bin/uvicorn main:app --host 0.0.0.0 --port 8000",
    directory="/home/deploy/my_app",
    user="deploy"
)

if not check_supervisor_installed(connection):
    install_supervisor(connection)

deploy_supervisor_service(connection, service)
supervisor_start(connection, "my_app")
```

## Examples

### Deploy FastAPI app

```python
from pyeasydeploy import *

conn = connect_to_host(host="vps.example.com", user="deploy", key_filename="~/.ssh/deploy_key")
python = get_target_python_instance(conn, "3.11")
venv = create_venv(conn, python, "/home/deploy/myapp_venv")

install_packages(conn, venv, ["fastapi", "uvicorn[standard]", "sqlalchemy"])
upload_directory(conn, "./myapp", "/home/deploy/myapp")

service = SupervisorService(
    name="myapp",
    command=f"{venv.venv_path}/bin/uvicorn main:app --host 0.0.0.0 --port 8000",
    directory="/home/deploy/myapp",
    user="deploy"
)

if not check_supervisor_installed(conn):
    install_supervisor(conn)

deploy_supervisor_service(conn, service)
supervisor_start(conn, "myapp")

print("✅ Deployed! Visit http://vps.example.com:8000")
```

### Install from GitHub + local package

```python
from pyeasydeploy import *

conn = connect_to_host(host="192.168.1.100", user="deploy", password="temp123")
python = get_target_python_instance(conn, "3.11")
venv = create_venv(conn, python, "/home/deploy/venv")

# Install from PyPI
install_packages(conn, venv, ["requests", "pandas"])

# Install from GitHub
install_package_from_github(conn, venv, "https://github.com/user/cool-package")

# Install your local package
install_local_package(conn, venv, "./my_local_package")
```

### Mix with pure Fabric commands

```python
from pyeasydeploy import *

conn = connect_to_host(host="server.com", user="deploy", key_filename="~/.ssh/id_rsa")

# Use pyeasydeploy
python = get_target_python_instance(conn, "3.11")
venv = create_venv(conn, python, "/home/deploy/venv")
install_packages(conn, venv, ["flask"])

# Use pure Fabric
conn.run("df -h")  # Check disk
conn.sudo("systemctl restart nginx")  # Restart nginx
conn.run("tail -100 /var/log/myapp.log")  # Check logs

# Back to pyeasydeploy
supervisor_restart(conn, "myapp")
```

### Update existing deployment

```python
from pyeasydeploy import *

conn = connect_to_host(host="vps.example.com", user="deploy", key_filename="~/.ssh/deploy_key")

# Upload new code
upload_directory(conn, "./myapp", "/home/deploy/myapp")

# Restart service
supervisor_restart(conn, "myapp")
supervisor_status(conn, "myapp")
```

### Run custom commands in venv

```python
from pyeasydeploy import *

conn = connect_to_host(host="server.com", user="deploy", password="pass")
python = get_target_python_instance(conn, "3.11")
venv = create_venv(conn, python, "/home/deploy/venv")

# Run migrations
run_in_venv(conn, venv, "alembic upgrade head")

# Run custom script
run_in_venv(conn, venv, "python scripts/seed_db.py")
```

## API Reference

### Connection

```python
# With SSH key (recommended)
connect_to_host(host, user, key_filename="/path/to/key", port=22)

# With password (testing only)
connect_to_host(host, user, password="...", port=22)
```

### Python & Venv

```python
get_python_instances(conn)  # List all Python versions
get_target_python_instance(conn, "3.11")  # Get specific version
create_venv(conn, python_instance, "/path/to/venv")
run_in_venv(conn, venv, "command")
```

### Packages

```python
install_packages(conn, venv, ["pkg1", "pkg2==1.0.0"])
install_local_package(conn, venv, "./local_package")
install_package_from_github(conn, venv, "https://github.com/user/repo")
```

### File Transfer

```python
upload_file(conn, "./local/file.py", "/remote/path/file.py")
upload_directory(conn, "./local_dir", "/remote/dir")
```

### Supervisor

```python
install_supervisor(conn)
check_supervisor_installed(conn)

service = SupervisorService(
    name="myapp",
    command="/path/to/command",
    directory="/working/dir",
    user="username"
)

deploy_supervisor_service(conn, service)
supervisor_start(conn, "myapp")
supervisor_stop(conn, "myapp")
supervisor_restart(conn, "myapp")
supervisor_status(conn, "myapp")
```

## Requirements

- Python 3.8+
- fabric
- paramiko

## Contributing

PRs welcome! This is a small tool I built for myself. If there's interest, I'll publish to PyPI and add more features.

## License

MIT
