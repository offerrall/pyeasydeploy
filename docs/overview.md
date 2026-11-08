# Overview

## What a deploy does

The introductory example is a complete deploy. Each call is one step, run over SSH in order, and each returns the value the next one takes:

1. `Server` describes the server: its address, user, and either a `Password` or a `Key`. Nothing connects yet; the value is only validated. The library opens one SSH connection per `Server` the first time a function needs it, and reuses it.
2. `ensure_uv` puts the [uv](https://docs.astral.sh/uv/) binary in `~/.pyeasydeploy/bin/uv`. It asks GitHub for the latest release and compares it with `uv --version` on the server: when they match, nothing is downloaded. Otherwise your machine downloads the build for the server's processor (`x86_64` or `aarch64`) and uploads it.
3. `ensure_python` has uv install the Python you ask for in `~/.pyeasydeploy/python/`, upgraded to its latest patch release. The system's Python is never used: a distribution upgrade cannot change or remove the interpreter your app runs on.
4. `deploy_app` packs your project, uploads it to a new release directory, and runs `uv sync --frozen` there, so the server gets exactly the versions of your `uv.lock`. Then it points `current` at the new release, writes a systemd user service for the app, and restarts it. The two newest releases are kept.

The app runs while the new release installs, and stops only for the restart. Its output goes to the systemd journal, which rotates it on its own: read it with `app_logs`.

On the server, everything lives in one folder, and the library refuses to remove anything outside it:

```text
~/.pyeasydeploy/
  bin/uv
  python/                         Pythons installed by uv
  cache/                          uv's cache
  apps/web/
    releases/20261108T183000Z/    the code and its .venv
    current -> releases/20261108T183000Z
    pyeasydeploy-web.service      the systemd user service
```

## Requirements

- **Your machine:** Windows, macOS or Linux, with SSH access to the server and to GitHub.
- **Your project:** a `pyproject.toml` and a `uv.lock` (run `uv lock` in it).
- **The server:** Linux on `x86_64` or `aarch64`, with SSH, systemd and access to GitHub and PyPI. No Python, no packages, no sudo.
- **Once, as root on the server:** `loginctl enable-linger deploy` (with your user), so the user's services start when the server boots and keep running after you log out. `deploy_app` checks it first and tells you the command if it is missing.

## Where to go next

- [Guide](guide.md): each part of a deploy in detail, with the options that change it.
- [Reference](reference.md): every public name.
- [Reproducibility](reproducibility.md): how far "same script, same server" reaches.
- [Design](design.md): the principles, and what the library deliberately does not do.
