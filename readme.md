# pyeasydeploy

Simple Python server deployment toolkit. Deploy to remote servers with just a few lines of code.

## Why?

Tired of SSHing manually but Kubernetes is overkill for your $5 VPS? This is for you.

- **300 lines of code** - Read and understand it in minutes
- **Simple API** - If you can write Python, you can deploy
- **Built on Fabric** - Mix with pure Fabric commands anytime

## Installation

```bash
pip install git+https://github.com/offerrall/pyeasydeploy.git
```

## Examples

### Deploy fast api app with supervisor

```python
from pyeasydeploy import *
from getpass import getpass

IP = "192.168.0.100"
USER = "offeytb"
PASSWORD = getpass("Enter the password for the remote user: ")
NAME_PROGRAM = "pyshop_secrets"
PROGRAM_FOLDER = f"./{NAME_PROGRAM}"

connection = connect_to_host(
    host=IP,
    user=USER,
    password=PASSWORD
)

app_folder_dest = f"/home/{USER}/{NAME_PROGRAM}"
venv_path = f"{app_folder_dest}/.venv"

connection.run(f"mkdir -p {app_folder_dest}")

upload_directory(connection, PROGRAM_FOLDER, app_folder_dest)

python = get_any_python_instance(connection)
venv = create_venv(connection, python, venv_path)

install_packages(connection, venv, ["fastapi", "uvicorn", "tinydb"])

service = SupervisorService(
    name=NAME_PROGRAM,
    command=f"{venv.venv_path}/bin/uvicorn main:app --host 0.0.0.0 --port 9101",
    directory=app_folder_dest,
    user=USER
)

if not check_supervisor_installed(connection):
    install_supervisor(connection)

deploy_supervisor_service(connection, service)

connection.sudo("supervisorctl reread")
connection.sudo("supervisorctl update")
connection.sudo(f"supervisorctl restart {NAME_PROGRAM}")
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
get_any_python_instance(conn)  # Get any available Python version (first found)
create_venv(conn, python_instance, "/path/to/venv") # if not exists, creates venv
run_in_venv(conn, venv, "command")
delete_venv(conn, "/path/to/venv")  # deletes existing venv
```

### Packages

```python
install_packages(conn, venv, ["pkg1", "pkg2==1.0.0"])
install_local_package(conn, venv, "./local_package")
install_package_from_github(conn, venv, "https://github.com/user/repo")
```

### File Transfer

```python
upload_file(conn, "./local/file.py", "/remote/path/file.py", remove_if_exists=True)
upload_directory(conn, "./local_dir", "/remote/dir", remove_if_exists=True)
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
