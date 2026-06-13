# pyeasydeploy 0.1.0

A small library for deploying Python applications to Linux servers over SSH. Plain Python functions on top of [Fabric](https://www.fabfile.org/): no agents on the server, no YAML, no DSL to learn. Your deploy script reads top to bottom.

It doesn't try to compete with Ansible or Docker. If you have a few servers, you write Python, and you want your deploy to be just another `deploy.py` in your project, it might be for you.

## A complete deploy

```python
from pyeasydeploy import (
    SupervisorService, connect_to_host, create_venv,
    deploy_supervisor_service, get_target_python_instance,
    install_local_package,
)

APP = "myapp"
USER = "deploy"

conn = connect_to_host(
    host="203.0.113.10",
    user=USER,
    key_filename="~/.ssh/id_ed25519",
    sudo_password="...",   # better: os.environ["SUDO_PASSWORD"]
)

py = get_target_python_instance(conn, "3.11")
venv = create_venv(conn, py, f"/home/{USER}/venvs/{APP}")
install_local_package(conn, venv, f"./{APP}")

deploy_supervisor_service(conn, SupervisorService(
    name=APP,
    command=f"{venv.venv_path}/bin/python -m {APP}",
    directory=f"/home/{USER}",
    user=USER,
))
```

Connect, pick an interpreter, create the venv, install your package with its dependencies, and leave it running as a supervised service that survives reboots. The `venv` object returned by `create_venv` carries its own path: the service command is built from it, no paths repeated by hand.

## The ideas behind it

**Destructive and reproducible.** Uploads remove the destination and copy from scratch, every time. After each deploy, the server has exactly what you have locally — no leftovers from previous versions. This is not configurable; it's the contract. (The one safety net: paths like `/`, `/home` or `/etc` are rejected as destinations.)

**Fail early, fail clearly.** Models validate on construction: a relative path or a service name that would corrupt the INI file blows up on your laptop with a useful message, before touching the server. Functions that need sudo check for it upfront — an immediate error with instructions, instead of the classic hang waiting for a password that will never come.

**Trust the user.** The library validates *form* (types, absolute paths, dangerous characters), not your *facts*: if you hand-build a `PythonInstance` pointing at an exotic interpreter, it's accepted. You know what's on your server.

## Installation

```bash
pip install pyeasydeploy
```

Python ≥ 3.10 on your machine. On the server: SSH and some `python3` (tested on Debian/Ubuntu).

## Quick guide

### Connecting

```python
conn = connect_to_host(host, user, password="...")                    # password (reused for sudo)
conn = connect_to_host(host, user, key_filename="~/.ssh/id_ed25519")  # SSH key
```

With key auth and sudo operations, add `sudo_password=`. The connection is lazy: a wrong password shows up on the first command, not at connect time.

### Remote Python

```python
py = get_any_python_instance(conn)             # newest on the server
py = get_target_python_instance(conn, "3.11")  # a specific one
```

Only real interpreters are matched (`python3.X-config` and friends are filtered out), and version matching is component-wise: `"3.1"` means 3.1, not 3.11. For non-standard locations, build the model yourself:

```python
py = PythonInstance(version="3.12", executable="/opt/py312/bin/python3.12")
```

### Venvs and packages

```python
venv = create_venv(conn, py, "/home/deploy/venvs/myapp")  # idempotent

install_packages(conn, venv, ["fastapi", "uvicorn[standard]"])
install_local_package(conn, venv, "./myapp")
install_package_from_private_github(conn, venv, "git@github.com:org/private.git")

run_in_venv(conn, venv, "python -m myapp --check")
```

Installs use `uv` inside the venv (fast; `use_uv=False` for classic pip). Private repos are cloned **on your machine** with your own credentials, then the source is uploaded: the server never needs access to your GitHub.

### Files

```python
upload_directory(conn, "./data", "/home/deploy/data")
upload_file(conn, "config.toml", "/home/deploy/myapp/config.toml")
```

⚠️ Destructive: the destination is removed before copying. `.git`, `__pycache__`, venvs and similar are excluded by default (`DEFAULT_IGNORE`); pass `ignore=[]` to upload everything.

### Services

```python
install_supervisor(conn)   # once per server

deploy_supervisor_service(conn, SupervisorService(
    name="myapp",
    command=f"{venv.venv_path}/bin/python -m myapp",
    extra={
        "stdout_logfile_maxbytes": "10MB",   # any supervisord option,
        "stdout_logfile_backups": 5,         # passed through verbatim
        "stopsignal": "INT",
    },
))

supervisor_status(conn)
supervisor_restart(conn, "myapp")
```

Named fields cover the common cases; the `extra` dict accepts any supervisord option with no restrictions — the library only blocks what would corrupt the generated file.

## What it is not

- **Not Ansible/Terraform.** No inventories, no state, no declarative idempotency. Imperative on purpose.
- **Not provisioning.** It installs supervisor because services are its job, and that's where it stops: nginx, databases and the rest of your server are up to you.
- **No secret management.** The passwords you pass in are your environment's responsibility.
- **No fleet orchestration.** One connection, one server. For several, write a loop.
- **Linux targets only.** The source machine can be Windows, macOS or Linux.

For many of those cases, bigger tools will do it better. This one exists for when you don't need them.

## License

MIT