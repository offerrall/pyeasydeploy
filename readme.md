# pyeasydeploy 0.1.6

[![PyPI](https://img.shields.io/pypi/v/pygrbl_streamer.svg)](https://pypi.org/project/pyeasydeploy/)

A small library for deploying Python applications to Linux servers over SSH. Plain Python functions on top of [Fabric](https://www.fabfile.org/): no agents on the server, no YAML, no DSL to learn. Your deploy script reads top to bottom.

It doesn't try to compete with Ansible or Docker. If you have a few servers, you write Python, and you want your deploy to be just another `deploy.py` in your project, it might be for you.

## A complete deploy

```python
from pyeasydeploy import (
    SupervisorService, connect_to_host, create_venv,
    deploy_supervisor_service, get_target_python_instance,
    install_local_package, supervisor_restart,
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
supervisor_restart(conn, APP)
```

Connect, pick an interpreter, create the venv, install your package with its dependencies, and leave it running as a supervised service that survives reboots. The `venv` object returned by `create_venv` carries its own path: the service command is built from it, no paths repeated by hand.

## The ideas behind it

**Destructive and reproducible.** Uploads remove the destination and copy from scratch, every time; venvs are recreated, not reused. After each deploy, the server has exactly what your script says it should have — no leftovers from previous versions. (The one safety net: paths like `/`, `/home` or `/etc` are rejected before anything is removed.) See [Reproducibility](#reproducibility) for how far that guarantee reaches.

**Fail early, fail clearly.** Models validate on construction: a relative path or a service name that would corrupt the INI file blows up on your laptop with a useful message, before touching the server. Functions that need sudo check for it upfront — an immediate error with instructions, instead of the classic hang waiting for a password that will never come.

**Trust the user.** The library validates *form* (types, absolute paths, dangerous characters), not your *facts*: if you hand-build a `PythonInstance` pointing at an exotic interpreter, it's accepted. You know what's on your server.

## Installation

```bash
pip install pyeasydeploy
```

Python ≥ 3.10 on your machine. On the server: SSH and some `python3` (tested on Arch, Debian and Ubuntu).

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
venv = create_venv(conn, py, "/home/deploy/venvs/myapp")  # wiped and rebuilt

install_packages(conn, venv, ["fastapi", "uvicorn[standard]"])
install_local_package(conn, venv, "./myapp")
install_package_from_private_github(conn, venv, "git@github.com:org/private.git")

run_in_venv(conn, venv, "python -m myapp --check")
```

⚠️ **Changed in 0.1.5:** `create_venv` deletes the existing environment and builds a new one. If you relied on reuse, pass `recreate=False` explicitly.

```python
venv = create_venv(conn, py, "/home/deploy/venvs/myapp", recreate=False)
install_local_package(conn, venv, "./myapp", force=True)   # see below
```

Reuse is for development, when reinstalling a large environment on every run is expensive. It comes with a catch: pip compares **versions, not commits**, so new code shipped under the same version number is silently ignored and the server keeps running the old one. `force=True` (available on all four `install_*` functions) passes `--force-reinstall` and fixes it. With the default `recreate=True` you don't need it.

Installs use `uv` inside the venv (fast; `use_uv=False` for classic pip). Private repos are cloned **on your machine** with your own credentials, then the source is uploaded: the server never needs access to your GitHub.

### Files

```python
upload_directory(conn, "./data", "/home/deploy/data")
upload_file(conn, "config.toml", "/home/deploy/myapp/config.toml")

upload_directory(conn, "./data", "/home/deploy/data", mode=0o644)      # every file
upload_file(conn, "secrets.env", "/home/deploy/myapp/.env", mode=0o600)
```

⚠️ Destructive: the destination is removed before copying. `.git`, `__pycache__`, venvs and similar are excluded by default (`DEFAULT_IGNORE`); pass `ignore=[]` to upload everything.

Without `mode`, permissions are whatever SFTP decides, which depends on the machine you deploy from — pass it when two people deploying the same project must get the same result. In `upload_directory` it applies to every file in the tree; directories keep the remote umask.

### Services

```python
install_supervisor(conn)   # once per server; Arch/Debian detected automatically

deploy_supervisor_service(conn, SupervisorService(
    name="myapp",
    command=f"{venv.venv_path}/bin/python -m myapp",
    extra={
        "stdout_logfile_maxbytes": "10MB",   # any supervisord option,
        "stdout_logfile_backups": 5,         # passed through verbatim
        "stopsignal": "INT",
    },
))
supervisor_restart(conn, "myapp")

supervisor_status(conn)
```

Named fields cover the common cases; the `extra` dict accepts any supervisord option with no restrictions — the library only blocks what would corrupt the generated file. The public API is identical on every supported distribution; package manager, systemd unit and configuration path are selected from the remote `/etc/os-release`.

## Reproducibility

The goal: **after a deploy, the parts of the server the library owns are a function of your script, not of what was there before.** Run the same script twice, or run it against a fresh server, and you get the same result.

What that covers:

- **Uploads.** `upload_file` and `upload_directory` remove the destination first. The remote tree is exactly your local tree minus the ignored patterns. Add `mode=` and the permissions stop depending on the machine you deploy from too.
- **Venvs.** `create_venv` wipes and rebuilds by default. Packages you stopped declaring disappear, pinned versions really apply, and changing the target Python version actually changes the interpreter — none of which happens in a reused venv.
- **Services.** The `.conf` for a deployed service is rewritten from the `SupervisorService` model every time. What you declare is what supervisord reads.

What it does **not** cover — real gaps, not oversights:

- **System packages and OS state.** pacman/apt, users, nginx, databases, firewall, cron. Out of scope; the library doesn't touch them (the one exception is `install_supervisor`, because services are its job).
- **Files the app creates at runtime.** Databases, logs, uploads, caches. They live wherever your app puts them and survive every deploy — which is normally what you want. If one lands inside an upload destination, it gets wiped: keep runtime data outside deploy directories.
- **Services deployed by previous runs.** `deploy_supervisor_service` manages the service you hand it and nothing else. Services from earlier runs stay untouched, and stay running.

### Known limitation: orphan services

There is no `prune`. If you rename a service — say `myapp` becomes `myapp-web` — the new `.conf` is deployed and started, and the old `myapp` **keeps running with the old code**, from a venv you may have just rebuilt underneath it. Same if you drop a service from your script: it isn't removed, it just stops being managed.

A `deploy_supervisor_services(services, prune=True)` that deleted every `.conf` not declared would be the coherent thing to do, but on a host shared with other apps it would take down services this library never deployed. Too much blast radius for now. Until then, removing a service is manual:

```python
conn.sudo("supervisorctl stop myapp")
conn.sudo("rm /etc/supervisor/conf.d/myapp.conf")  # Debian/Ubuntu
# conn.sudo("rm /etc/supervisor.d/myapp.ini")      # Arch
conn.sudo("supervisorctl update")
```

## What it is not

- **Not Ansible/Terraform.** No inventories, no state, no declarative idempotency. Imperative on purpose.
- **Not provisioning.** It installs supervisor because services are its job, and that's where it stops: nginx, databases and the rest of your server are up to you.
- **No secret management.** The passwords you pass in are your environment's responsibility.
- **No fleet orchestration.** One connection, one server. For several, write a loop.
- **Linux targets only.** The source machine can be Windows, macOS or Linux.

For many of those cases, bigger tools will do it better. This one exists for when you don't need them.

## License

MIT
