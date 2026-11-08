# Guide

Every name used here is imported from `pyeasydeploy`. `server`, `uv` and `python` are the values created in the sections before. The [Reference](reference.md) lists every public name.

## Servers

```python
from pyeasydeploy import Key, Password, Server

server = Server(address="203.0.113.10", user="deploy", auth=Key(path="~/.ssh/id_ed25519"))
server = Server(address="203.0.113.10", user="deploy", auth=Password(value="..."), port=2222)
```

`auth` is either a `Password` or a `Key`, so a server always has exactly one. A `Server` is only a value: building it connects to nothing. The first function that needs the server opens an SSH connection, and every later call with an equal `Server` reuses it.

All models are immutable, take keyword arguments and validate themselves when built: a relative path, a port out of range or an app name with a space fails on your machine, before anything reaches the server. To change one, build another with `dataclasses.replace`.

## uv and Python

```python
uv = ensure_uv(server)                          # the latest uv release
uv = ensure_uv(server, url="https://example.com/my-uv.tar.gz")
uv = ensure_uv(server, url="file:///home/me/uv-x86_64-unknown-linux-musl.tar.gz")

python = ensure_python(uv, "3.13")              # the latest 3.13.x
python = ensure_python(uv, "3.13.9")            # exactly 3.13.9
```

`ensure_uv` uploads uv only when the server does not have the latest release. With `url`, it uses that `.tar.gz` as it is, whatever processor the server has: the archive must hold a file named `uv`, and it is uploaded only when it differs from the one on the server. `file://` URLs work, for a uv on your own disk.

`ensure_python` installs with uv into `~/.pyeasydeploy/python/`. A version like `"3.13"` gets the newest patch release the server's uv knows, upgrading an older one on every deploy; a full version like `"3.13.9"` stays fixed. The returned `Python` holds the exact version installed.

## Apps

```python
from pyeasydeploy import App, deploy_app

release = deploy_app(python, App(name="web", source="./web", command="python -m web"))
release = deploy_app(python, App(name="web", source="./web", command="web --port 8000"))
release = deploy_app(python, App(name="web", source=".", command="web", package="web"))
release = deploy_app(python, App(name="web", source="./web", command="web",
                                 environment=(("NTFY_TOPIC", "shop"), ("PORT", "8000"))))
```

`source` is the folder on your machine with the project's `pyproject.toml` and `uv.lock`. It is uploaded without `.git`, virtual environments, caches, `*.pyc` or local databases (`*.db`, `*.sqlite`, `*.sqlite3`). `package` selects one member of a uv workspace: `source` is then the workspace root, where `uv.lock` lives. With `package`, only what `uv.lock` points to is uploaded: the root's `pyproject.toml` and `uv.lock`, and the folders of its local packages. Everything else in the root, such as data or other projects, stays on your machine. A lock that points outside `source` is refused. Without `package`, the whole folder is the app, packaged or not: `command="python main.py"` works for a project with no build system.

`environment` holds the app's environment variables, as `(name, value)` pairs. They are written into the service's file, which only your user can read.

`command` runs from the release's virtual environment, in the release's folder: its first word is a program in the venv's `bin/` (`python`, or a script your project declares), and the rest are its arguments. The service restarts it whenever it exits.

`deploy_app` installs the new release while the old one keeps running, switches `current` to it and restarts the service. If the install fails, the new release is removed and the app keeps running the old one. If the command cannot be started, for example because the program does not exist in the venv, `deploy_app` raises instead of returning; a program that starts and then crashes shows up in `app_status` and `app_logs`. The two newest releases are kept, so the previous one is still on disk.

## Logs and control

```python
from pyeasydeploy import app_logs, app_status, restart_app, stop_app

print(app_status(server, "web"))
print(app_logs(server, "web", lines=50))
restart_app(server, "web")
stop_app(server, "web")
```

Everything the app prints, output and errors alike, goes to the systemd journal in order, as in a terminal. The journal rotates and limits it on its own: there are no log files to manage. For the journal to survive a reboot it must be kept on disk, which is the default on most distributions.

## The escape hatch

```python
from pyeasydeploy import fabric_connection

fabric_connection(server).run("df -h")
```

`fabric_connection` returns the [Fabric](https://www.fabfile.org/) connection the library uses for that server, for anything the library does not do. What you run there is up to you: the library's limits, such as staying inside `~/.pyeasydeploy`, do not apply.
