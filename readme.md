# pyeasydeploy

Simple Python server deployment toolkit. Deploy to remote servers with just a few lines of code.

## Why?

Tired of SSHing manually but Kubernetes is overkill for your $5 VPS? This is for you.

- **Tiny codebase** — read it in minutes, no magic.
- **Minimalist API by design** — every function does one thing and only takes what it needs. Nothing hidden, nothing global.
- **Hard to misuse** — the API is built around small immutable classes (`PythonInstance`, `VenvPython`, `SupervisorService`). You can't pass the wrong thing to the wrong function. If your code typechecks, it'll likely run.
- **Built on Fabric** — drop down to raw Fabric commands at any point. No abstraction lock-in.
- **Fast deploys** — uses `uv` under the hood for package installation, with `pip` as fallback.

## Design philosophy

The API is built on a few small immutable types that flow through the functions:

```python
python = get_any_python_instance(conn)         # -> PythonInstance
venv   = create_venv(conn, python, "/path")    # -> VenvPython (carries python info)
install_packages(conn, venv, ["fastapi"])      # consumes VenvPython
```

You can't `install_packages` without first having a `VenvPython`. You can't get a
`VenvPython` without a `PythonInstance`. The dependency chain is enforced by the
types themselves, so the order of operations is obvious and mistakes are caught
before runtime.

There's no global config, no implicit state, no "init" call. Each function takes
the connection and the data it needs, and returns the data the next step needs.

## Installation

PyPI is coming soon. For now, install directly from GitHub:

```bash
pip install git+https://github.com/offerrall/pyeasydeploy.git
```

## Examples

### Deploy a FastAPI app with supervisor

```python
from pyeasydeploy import *
from getpass import getpass

IP = "192.168.0.100"
USER = "offeytb"
PASSWORD = getpass("Enter the password for the remote user: ")
NAME_PROGRAM = "pyshop_secrets"
PROGRAM_FOLDER = f"./{NAME_PROGRAM}"

connection = connect_to_host(host=IP, user=USER, password=PASSWORD)

app_folder_dest = f"/home/{USER}/{NAME_PROGRAM}"
venv_path = f"{app_folder_dest}/.venv"

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
supervisor_restart(connection, NAME_PROGRAM)
```

### Mix with pure Fabric commands

```python
from pyeasydeploy import *

conn = connect_to_host(host="server.com", user="deploy", key_filename="~/.ssh/id_rsa")

# Use pyeasydeploy
python = get_target_python_instance(conn, "3.11")
venv = create_venv(conn, python, "/home/deploy/venv")
install_packages(conn, venv, ["flask"])

# Use pure Fabric whenever you need
conn.run("df -h")
conn.sudo("systemctl restart nginx")
conn.run("tail -100 /var/log/myapp.log")

# Back to pyeasydeploy
supervisor_restart(conn, "myapp")
```

### Update an existing deployment

```python
from pyeasydeploy import *

conn = connect_to_host(host="vps.example.com", user="deploy", key_filename="~/.ssh/deploy_key")

# Upload new code (overwrite existing; pass remove_if_exists=False to merge)
upload_directory(conn, "./myapp", "/home/deploy/myapp", remove_if_exists=True)

supervisor_restart(conn, "myapp")
supervisor_status(conn, "myapp")
```

### Install from a private GitHub repo

The server doesn't need any GitHub credentials. The repo is cloned locally
(using your client's Git auth) and uploaded to the server.

```python
from pyeasydeploy import *

conn = connect_to_host(host="server.com", user="deploy", key_filename="~/.ssh/id_rsa")
python = get_target_python_instance(conn, "3.11")
venv = create_venv(conn, python, "/home/deploy/venv")

install_package_from_private_github(
    conn, venv,
    "git@github.com:myorg/my-private-package.git",
    branch="v1.2.0"
)
```

### Run custom commands inside the venv

```python
from pyeasydeploy import *

conn = connect_to_host(host="server.com", user="deploy", password="pass")
python = get_target_python_instance(conn, "3.11")
venv = create_venv(conn, python, "/home/deploy/venv")

run_in_venv(conn, venv, "alembic upgrade head")
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
get_python_instances(conn)                   # List all Python versions on the host
get_target_python_instance(conn, "3.11")     # Get a specific version
get_any_python_instance(conn)                # Get any available Python (first found)

create_venv(conn, python_instance, "/path/to/venv")   # idempotent: skips if exists
run_in_venv(conn, venv, "command")
delete_venv(conn, venv)
```

`create_venv` automatically installs `uv` inside the venv so package operations
are fast. This is idempotent — running it on an existing venv is a no-op.

### Packages

By default, all package functions use `uv` for speed (set `use_uv=False` to fall
back to `pip`).

```python
install_packages(conn, venv, ["pkg1", "pkg2==1.0.0"])
install_local_package(conn, venv, "./local_package")
install_package_from_github(conn, venv, "https://github.com/user/repo")

# Private repos: cloned on the client, uploaded to the server.
# The server needs no GitHub auth. Requires `git` installed locally.
install_package_from_private_github(conn, venv, "git@github.com:user/repo.git", branch="main")
```

### File Transfer

```python
upload_file(conn, "./local/file.py", "/remote/path/file.py", remove_if_exists=True)
upload_directory(conn, "./local_dir", "/remote/dir", remove_if_exists=True)
```

`upload_directory` automatically skips common junk that shouldn't be deployed:
`.git`, `.venv`, `__pycache__`, IDE folders, `*.pyc`, local SQLite files, etc.
This keeps deploys fast and avoids shipping development artifacts to the server.

You can override the filter with the `ignore` parameter (accepts globs via
`fnmatch`):

```python
# Use your own list (replaces the defaults)
upload_directory(conn, "./myapp", "/home/deploy/myapp", ignore=[".git", "*.log"])

# Disable filtering entirely (upload everything)
upload_directory(conn, "./myapp", "/home/deploy/myapp", ignore=[])

# Extend the defaults
from pyeasydeploy import DEFAULT_IGNORE
upload_directory(conn, "./myapp", "/home/deploy/myapp", ignore=DEFAULT_IGNORE + ["secrets.env"])
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

`SupervisorService` is a `NamedTuple` — immutable, fully typed, with sane
defaults for `autostart`, `autorestart`, and log paths. You build it once,
pass it around, and it can't be modified by accident.

## Requirements

- Python 3.8+
- fabric
- paramiko
- git (only on the client, for `install_package_from_private_github`)

## Contributing

PRs welcome! This is a small tool I built for myself. If there's interest, I'll publish to PyPI and add more features.

## License

MIT