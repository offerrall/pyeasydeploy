# Reference

Every public name, importable from `pyeasydeploy`. Models take keyword arguments only, are deeply immutable, and raise `SchemaTypeError` or `SchemaValueError` (subclasses of `TypeError` and `ValueError`) naming the field when a value is invalid. Every function that talks to the server takes the connection first; most also take `verbose=True`, which prints each step.

## Models

| Name | Fields | Notes |
|---|---|---|
| `Host` | `address`, `user`, `auth`, `sudo_password=None`, `port=22` | A server. `auth` is a `Password` or a `Key`. sudo uses `sudo_password`, or the SSH password when `auth` is a `Password`. |
| `Password` | `value` | SSH password, not empty. |
| `Key` | `path` | An SSH private key file on your machine, e.g. `"~/.ssh/id_ed25519"`. |
| `PythonInstance` | `version`, `executable` | An interpreter on the server. `version` looks like `"3"` or `"3.11"`; `executable` is an absolute path. |
| `Venv` | `python`, `path` | A virtual environment on the server, bound to the `PythonInstance` that created it. `path` is absolute. |
| `SupervisorService` | `name`, `command`, `directory=None`, `user=None`, `autostart=True`, `autorestart=True`, `stdout_logfile`, `stderr_logfile`, `environment=None`, `extra=()` | A supervisord `[program:name]` entry. Fields set to `None` are left out of the file. The log files default to `/var/log/supervisor/%(program_name)s.log` and `%(program_name)s_err.log`. |
| `Option` | `key`, `value` | One supervisord option for `SupervisorService.extra`, written as `key=value`. `value` is a one-line `str`, an `int` or a `bool` (written `true`/`false`). |

## Connection

| Function | Does |
|---|---|
| `connect(host)` | An SSH connection (a Fabric `Connection`) to a `Host`. Lazy: a wrong password shows up on the first command. |
| `has_sudo_password(conn)` | Whether the connection has a sudo password. |
| `require_sudo(conn, what="this operation")` | Raises `PermissionError` at once if sudo would hang waiting for a password. |

## Remote Python

| Function | Does |
|---|---|
| `get_python_instances(conn)` | The `python3` interpreters in `/usr/bin`, newest first. `RuntimeError` if there is none. |
| `get_target_python_instance(conn, target_version)` | The newest interpreter matching `target_version` by components: `"3.1"` matches 3.1 only, `"3"` any 3.x. `RuntimeError` listing the available versions if none matches. |
| `get_any_python_instance(conn)` | The newest `python3` interpreter. |

## Venvs

| Function | Does |
|---|---|
| `create_venv(conn, python, path, recreate=True)` | Creates a `Venv` at `path` with `uv` installed in it and returns it. By default an existing venv there is removed first; `recreate=False` reuses it. |
| `delete_venv(conn, venv)` | Removes the venv's directory. |
| `run_in_venv(conn, venv, command, hide=False)` | Runs a shell command with the venv's `bin/` first in `PATH`. The command reaches the remote shell as is. Returns Fabric's result. |

## Packages

All four take `use_uv=True` (`False` installs with pip) and `force=False` (`True` passes `--force-reinstall`).

| Function | Does |
|---|---|
| `install_packages(conn, venv, packages)` | Installs requirement specifiers from PyPI, e.g. `["fastapi", "requests>=2.31"]`. |
| `install_local_package(conn, venv, local_package_dir)` | Uploads a local package (`pyproject.toml` or `setup.py` at its root) to a temporary directory and installs it with its dependencies. |
| `install_package_from_github(conn, venv, github_repo_url)` | Installs from a repository the server can clone itself. |
| `install_package_from_private_github(conn, venv, github_repo_url, branch=None)` | Clones on your machine with your git credentials, then uploads the source and installs it. |

## Files

Both remove the destination first, and refuse system roots such as `/`, `/etc`, `/home`, `/usr` or `/var` with `ValueError`.

| Name | Does |
|---|---|
| `upload_file(conn, local_file, remote_file, mode=None)` | Replaces `remote_file` with the local file, creating its parents. `mode` (e.g. `0o600`) sets its permissions. |
| `upload_directory(conn, local_dir, remote_dir, ignore=None, mode=None)` | Replaces `remote_dir` with a copy of `local_dir`. `ignore` holds name patterns; `None` means `DEFAULT_IGNORE`, `[]` uploads everything. `mode` applies to every file. |
| `DEFAULT_IGNORE` | The name patterns skipped by default: `.git`, `.venv`, `venv`, `__pycache__`, `.vscode`, `.idea`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `*.pyc`, `*.pyo`, `*.db`, `*.sqlite`, `*.sqlite3`, `.DS_Store`. |

## Services

All of these need sudo, except `check_supervisor_installed` and `create_supervisor_config`. Arch and Debian-based servers are supported, detected from `/etc/os-release`.

| Function | Does |
|---|---|
| `install_supervisor(conn)` | Installs, enables and starts supervisord. Safe to run again. |
| `check_supervisor_installed(conn)` | Whether `supervisorctl` is on the server. |
| `create_supervisor_config(service)` | The INI text for a `SupervisorService`: the named fields that are not `None`, then `extra` in order. Local, touches no server. |
| `deploy_supervisor_service(conn, service)` | Writes the service's configuration, replacing any with the same name, and reloads supervisord. It starts if `autostart` is set; a running service whose configuration changed is restarted. |
| `supervisor_start(conn, service_name)` | `supervisorctl start`. |
| `supervisor_stop(conn, service_name)` | `supervisorctl stop`. |
| `supervisor_restart(conn, service_name)` | `supervisorctl restart`. |
| `supervisor_status(conn, service_name=None)` | `supervisorctl status` of one service, or of all when `service_name` is `None`. |
