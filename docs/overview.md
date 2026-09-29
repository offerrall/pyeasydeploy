# Overview

## What a deploy does

The introductory example is a complete deploy. Each call is one step, run over SSH in order:

1. `connect` opens a connection to the `Host`: its address, user, and either a `Password` or a `Key`. Operations that need sudo use `sudo_password`, or the SSH password when `auth` is a `Password`. The connection is lazy: a wrong password shows up on the first command.
2. `get_target_python_instance` picks an interpreter already installed on the server: the newest one whose version matches `"3.11"`.
3. `create_venv` builds a virtual environment with that interpreter, removing any previous one at the same path.
4. `install_local_package` uploads your local package and installs it in the venv with its dependencies.
5. `deploy_supervisor_service` writes a supervisord entry for the app and reloads supervisord, so the app runs as a service that restarts on failure and survives reboots. `supervisor_restart` then restarts it, so it runs the new code even when its configuration did not change.

The `venv` object returned by `create_venv` carries its own path, so the service command is built from it and no path is repeated by hand. Run the script again and the server ends up in the same state: see [Reproducibility](reproducibility.md).

The models (`Host`, `Key`, `SupervisorService` and the rest) validate themselves when built, so a relative path or a malformed service name fails on your machine before anything reaches the server. Keep secrets out of the script: read `sudo_password` from the environment, for example `os.environ["SUDO_PASSWORD"]`.

## Requirements

- **Your machine:** Windows, macOS or Linux, with SSH access to the server.
- **The server:** Linux with SSH and a `python3` in `/usr/bin`. Tested on Arch, Debian and Ubuntu.
- **Services:** supervisord is installed and managed on Arch and on Debian-based distributions (Debian, Ubuntu), detected from `/etc/os-release`. Managing services needs sudo on the server.

## Where to go next

- [Guide](guide.md): each part of a deploy in detail, with the options that change it.
- [Reference](reference.md): every public name.
- [Reproducibility](reproducibility.md): how far "same script, same server" reaches.
- [Design](design.md): the principles, and what the library deliberately does not do.
