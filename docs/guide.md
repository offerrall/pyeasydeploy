# Guide

Every name used here is imported from `pyeasydeploy`. `conn`, `py` and `venv` are the values created in the sections before. The [Reference](reference.md) lists every public name.

## Connecting

```python
from pyeasydeploy import Host, Key, Password, connect

conn = connect(Host(address="203.0.113.10", user="deploy", auth=Password(value="...")))          # reused for sudo
conn = connect(Host(address="203.0.113.10", user="deploy", auth=Key(path="~/.ssh/id_ed25519")))  # SSH key
conn = connect(Host(address="203.0.113.10", user="deploy", auth=Key(path="..."), sudo_password="...", port=2222))
```

`auth` is either a `Password` or a `Key`, so a host always has exactly one. With a key and sudo operations, add `sudo_password`. Functions that need sudo check for a password first and raise `PermissionError` at once, instead of hanging while sudo waits for one. The connection is lazy: a wrong password shows up on the first command, not at connect time.

All models are immutable, take keyword arguments and validate themselves when built: a relative path, a port out of range or a blank name fails on your machine, before anything reaches the server.

## Remote Python

```python
py = get_any_python_instance(conn)             # newest on the server
py = get_target_python_instance(conn, "3.11")  # a specific one
found = get_python_instances(conn)             # all of them, newest first
```

Interpreters are looked up in `/usr/bin`. Only real interpreters are matched (`python3.X-config` and friends are filtered out), and version matching is component-wise: `"3.1"` means 3.1, not 3.11. For non-standard locations, build the model yourself:

```python
py = PythonInstance(version="3.12", executable="/opt/py312/bin/python3.12")
```

## Venvs and packages

```python
venv = create_venv(conn, py, "/home/deploy/venvs/myapp")  # wiped and rebuilt

install_packages(conn, venv, ["fastapi", "uvicorn[standard]"])
install_local_package(conn, venv, "./myapp")
install_package_from_github(conn, venv, "https://github.com/org/public.git")
install_package_from_private_github(conn, venv, "git@github.com:org/private.git", branch="main")

run_in_venv(conn, venv, "python -m myapp --check")
delete_venv(conn, venv)
```

`create_venv` deletes an existing environment at that path and builds a new one. Pass `recreate=False` to reuse it:

```python
venv = create_venv(conn, py, "/home/deploy/venvs/myapp", recreate=False)
install_local_package(conn, venv, "./myapp", force=True)   # see below
```

Reuse is for development, when reinstalling a large environment on every run is expensive. It comes with a catch: pip compares **versions, not commits**, so new code shipped under the same version number is silently ignored and the server keeps running the old one. `force=True` (available on all four `install_*` functions) passes `--force-reinstall` and fixes it. With the default `recreate=True` you don't need it.

Installs use `uv` inside the venv (fast; `use_uv=False` for classic pip). `install_local_package` needs a `pyproject.toml` or `setup.py` at the package root; it uploads to a temporary directory on the server and removes it afterwards, even if the install fails. `install_package_from_github` has the server clone the repository itself. `install_package_from_private_github` clones **on your machine** with your own credentials, then uploads the source: the server never needs access to your GitHub. `run_in_venv` runs a shell command with the venv's `bin/` first in `PATH`, as `activate` would; quoting inside the command is up to you.

## Files

```python
upload_directory(conn, "./data", "/home/deploy/data")
upload_file(conn, "config.toml", "/home/deploy/myapp/config.toml")

upload_directory(conn, "./data", "/home/deploy/data", mode=0o644)      # every file
upload_file(conn, "secrets.env", "/home/deploy/myapp/.env", mode=0o600)
```

Uploads are destructive: the destination is removed before copying (see [Reproducibility](reproducibility.md)), and system roots such as `/`, `/home` or `/etc` are rejected as destinations. `upload_file` creates missing parent directories. `.git`, `__pycache__`, venvs and similar are excluded by default (`DEFAULT_IGNORE`); `ignore` takes name patterns, not paths, and `ignore=[]` uploads everything.

Without `mode`, permissions are whatever SFTP decides, which depends on the machine you deploy from: pass it when two people deploying the same project must get the same result. In `upload_directory` it applies to every file in the tree; directories keep the remote umask.

## Services

```python
install_supervisor(conn)   # once per server; Arch/Debian detected automatically

deploy_supervisor_service(conn, SupervisorService(
    name="myapp",
    command=f"{venv.path}/bin/python -m myapp",
    extra=(
        Option(key="stdout_logfile_maxbytes", value="10MB"),   # any supervisord option,
        Option(key="stdout_logfile_backups", value=5),         # written in this order
        Option(key="stopsignal", value="INT"),
    ),
))
supervisor_restart(conn, "myapp")

supervisor_start(conn, "myapp")
supervisor_stop(conn, "myapp")
supervisor_status(conn)            # every service; pass a name for one
```

`deploy_supervisor_service` writes the service's configuration, replacing any with the same name, and reloads supervisord: the service starts if `autostart` is set, and a running service whose configuration changed is restarted. `install_supervisor` installs, enables and starts supervisord, and is safe to run again.

Named fields cover the common cases; fields set to `None` are left out of the file, so supervisord's defaults apply. `extra` accepts any other supervisord option with no restrictions: the library only blocks what would corrupt the generated file, a key that repeats a named field, or the same key twice. The public API is identical on every supported distribution; package manager, systemd unit and configuration path are selected from the remote `/etc/os-release`.
