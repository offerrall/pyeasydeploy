# Reference

Every public name, importable from `pyeasydeploy`. Models take keyword arguments only, are deeply immutable, and raise `SchemaTypeError` or `SchemaValueError` (subclasses of `TypeError` and `ValueError`) naming the field when a value is invalid. Functions that talk to the server take a model first and open, or reuse, the SSH connection of its `Server`.

## Models

| Name | Fields | Notes |
|---|---|---|
| `Server` | `address`, `user`, `auth`, `port=22` | A server. `auth` is a `Password` or a `Key`. |
| `Password` | `value` | SSH password, not empty. |
| `Key` | `path` | An SSH private key file on your machine, e.g. `"~/.ssh/id_ed25519"`. |
| `Uv` | `server`, `path` | The uv binary on a server. `path` is absolute. |
| `Python` | `uv`, `version`, `path` | A Python installed by that uv. `version` is the exact one, e.g. `"3.13.9"`; `path` is the interpreter. |
| `App` | `name`, `source`, `command`, `package=None`, `environment=()` | An app to deploy. `name` is letters, digits, `_`, `.` or `-`; `source` is a local folder with `pyproject.toml` and `uv.lock`; `command` is one line, run from the release's venv; `package` is a uv workspace member; `environment` holds `(name, value)` pairs, each value one line. |
| `Release` | `python`, `app`, `path` | One deployed copy of an app, in `~/.pyeasydeploy/apps/<name>/releases/`. |

## Server

| Function | Does |
|---|---|
| `fabric_connection(server)` | The Fabric `Connection` the library uses for `server`, opened on first use. The escape hatch: what runs through it is up to you. |
| `pyeasydeploy_dir(server)` | The absolute path of `~/.pyeasydeploy` on the server. |
| `server_arch(server)` | The server's processor, from `uname -m`, e.g. `"x86_64"`. |

## uv and Python

| Function | Does |
|---|---|
| `ensure_uv(server, url=None)` | Puts uv in `~/.pyeasydeploy/bin/uv` and returns a `Uv`. Without `url`, the latest release for the server's processor, downloaded only when the server's `uv --version` differs. With `url`, that `.tar.gz` as it is, uploaded only when its `uv` differs from the server's. `ValueError` for a processor other than `x86_64` or `aarch64`. |
| `ensure_python(uv, version)` | Installs Python `version` with uv into `~/.pyeasydeploy/python/` and returns a `Python`. `"3.13"` is upgraded to its latest patch release; `"3.13.9"` is exact. |

## Apps

| Function | Does |
|---|---|
| `deploy_app(python, app)` | Uploads `app.source` to a new release, installs it with `uv sync --frozen --no-dev`, points `current` at it, writes and enables the systemd user service `pyeasydeploy-<name>.service`, restarts it, and keeps the two newest releases. Returns the `Release`. `RuntimeError` with the command to run if lingering is not enabled for the user; `FileNotFoundError` if `source` has no `uv.lock`. A failed install removes its release. Raises if the service cannot start `command`. |
| `app_status(server, name)` | `systemctl --user status` of the app's service, as text. |
| `app_logs(server, name, lines=100)` | The last `lines` lines of the app's output, from the systemd journal. |
| `restart_app(server, name)` | Restarts the app's service. |
| `stop_app(server, name)` | Stops the app's service. It starts again on the next deploy or reboot. |
