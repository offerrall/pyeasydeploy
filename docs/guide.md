# Guide

## Connecting

```python
conn = connect(Host(address=host, user=user, auth=Password(value="...")))              # reused for sudo
conn = connect(Host(address=host, user=user, auth=Key(path="~/.ssh/id_ed25519")))      # SSH key
conn = connect(Host(address=host, user=user, auth=Key(path="..."), sudo_password="...", port=2222))
```

`auth` is either a `Password` or a `Key`, so a host always has exactly one. With a key and sudo operations, add `sudo_password`. The connection is lazy: a wrong password shows up on the first command, not at connect time.

All models are immutable, take keyword arguments and validate themselves when built: a relative path, a port out of range or a blank name fails on your machine, before anything reaches the server.

## Remote Python

```python
py = get_any_python_instance(conn)             # newest on the server
py = get_target_python_instance(conn, "3.11")  # a specific one
```

Only real interpreters are matched (`python3.X-config` and friends are filtered out), and version matching is component-wise: `"3.1"` means 3.1, not 3.11. For non-standard locations, build the model yourself:

```python
py = PythonInstance(version="3.12", executable="/opt/py312/bin/python3.12")
```

## Venvs and packages

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

## Files

```python
upload_directory(conn, "./data", "/home/deploy/data")
upload_file(conn, "config.toml", "/home/deploy/myapp/config.toml")

upload_directory(conn, "./data", "/home/deploy/data", mode=0o644)      # every file
upload_file(conn, "secrets.env", "/home/deploy/myapp/.env", mode=0o600)
```

⚠️ Destructive: the destination is removed before copying. `.git`, `__pycache__`, venvs and similar are excluded by default (`DEFAULT_IGNORE`); pass `ignore=[]` to upload everything.

Without `mode`, permissions are whatever SFTP decides, which depends on the machine you deploy from — pass it when two people deploying the same project must get the same result. In `upload_directory` it applies to every file in the tree; directories keep the remote umask.

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

supervisor_status(conn)
```

Named fields cover the common cases; `extra` accepts any other supervisord option with no restrictions — the library only blocks what would corrupt the generated file, a key that repeats a named field, or the same key twice. The public API is identical on every supported distribution; package manager, systemd unit and configuration path are selected from the remote `/etc/os-release`.

