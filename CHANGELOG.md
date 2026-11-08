# Changelog

## 2.0.0 - 2026-11-08

A new library under the same name. The server only needs SSH and systemd: the deploy
brings uv, Python and the app, with no sudo and no system packages, the same on any
distribution. Everything lives in `~/.pyeasydeploy` on the server.

### Changed (breaking)

- `connect(Host(...))` is gone. Functions take an immutable `Server` (`address`, `user`,
  `auth`, `port`) and the library keeps one SSH connection per `Server` inside.
  `fabric_connection(server)` returns it, for anything the library does not do.
  `sudo_password` is gone: nothing needs sudo.
- The interpreter comes from uv, not from `/usr/bin`: `ensure_uv(server)` uploads the
  latest uv (or the one at `url`), and `ensure_python(uv, "3.13")` installs Python with it.
  `get_python_instances`, `get_target_python_instance`, `get_any_python_instance` and
  `PythonInstance` are gone.
- Apps are deployed from their `uv.lock` with `deploy_app(python, App(...))`: each deploy is
  a new release with its own venv, `current` points at it, and the two newest are kept.
  Its `environment` sets the app's variables. With `package`, only what `uv.lock` points
  to in the workspace is uploaded. A command that cannot start makes the deploy fail.
  `create_venv`, `delete_venv`, `run_in_venv`, the four `install_*` functions,
  `upload_file`, `upload_directory` and `DEFAULT_IGNORE` are gone.
- Apps run as systemd user services instead of supervisord, and their output goes to the
  systemd journal: `app_status`, `app_logs`, `restart_app` and `stop_app`. Enabling
  lingering once, as root, is the only setup. `SupervisorService`, `Option` and the
  `supervisor_*` functions are gone.
- `pytypehint` is pinned to `==1.2.3`.

### Fixed

- Removals can no longer escape their folder: every path is normalized and must be
  strictly inside `~/.pyeasydeploy`, where 1.x checked a list of system roots that
  `/usr/../etc` or a home directory got past.
- The key path of a `Key` expands `~`.

### Added

- `examples/`: a small HTTP app with its `uv.lock`, and the `deploy.py` that deploys it.

## 1.0.4 - 2026-09-29

### Changed

- Documentation only: the README's Documentation list links each page on the
  documentation site, so readers on GitHub and PyPI land there. The code is the same as 1.0.3.

## 1.0.3 - 2026-09-29

### Changed

- Documentation only. The README becomes a short entrance to the documentation site,
  https://offerrall.github.io/pyeasydeploy/, and `docs/overview.md` holds the
  introduction: what each step of a deploy does, and what the server needs.
- A new `docs/reference.md` lists every public name. `get_python_instances`,
  `delete_venv`, `install_package_from_github`, `supervisor_start`, `supervisor_stop`,
  `has_sudo_password`, `require_sudo`, `check_supervisor_installed` and
  `create_supervisor_config` were documented nowhere; the guide's examples import what
  they use.
- `RELEASING.md` moves to `docs/releasing.md`. The "Changed in 0.1.5" note leaves the
  guide for its 0.1.5 entry here, and the changelog headings carry their release dates.
- `pyproject.toml`: the description matches the package docstring, and
  `[project.urls]` gains `Documentation`.

The code is the same as 1.0.2.

## 1.0.2 - 2026-09-29

### Added

- The `LICENSE` file with the MIT text that `pyproject.toml` declares, shipped in
  the package. The code is the same as 1.0.1.

## 1.0.1 - 2026-09-29

### Changed

- `pytypehint` is pinned to the exact version this release is tested with,
  `==1.2.1`, instead of `>=1.2`: a new pytypehint can no longer change what an
  installed pyeasydeploy does. The code is the same as 1.0.0.

## 1.0.0 - 2026-09-29

The models are rebuilt on [pytypehint](https://offerrall.github.io/pytypehint/): deeply
immutable, keyword-only, and validated from their types when built. What reaches the
server (commands, files, their order) is the same as in 0.1.6.

### Changed (breaking)

- Python 3.11 or newer, and `pytypehint` as a dependency.
- `connect_to_host(host, user, password=..., key_filename=..., sudo_password=..., port=...)`
  is now `connect(Host(address=..., user=..., auth=..., sudo_password=..., port=...))`, where
  `auth` is `Password(value=...)` or `Key(path=...)`: exactly one, by type.
- `VenvPython(venv_name, python_instance, venv_path)` is now `Venv(python=..., path=...)`;
  `create_venv(conn, python, path)` takes those names.
- `SupervisorService.extra` is a tuple of `Option(key=..., value=...)`, written in that
  order, instead of a dict. A key given twice is rejected.
- Models take keyword arguments only. Invalid values raise `SchemaTypeError` and
  `SchemaValueError` (subclasses of `TypeError` and `ValueError`), naming the field.

### Fixed

- The README is `README.md`, as `pyproject.toml` says: built on Linux, 0.1.6 had no long
  description.
- The PyPI badge showed another package's version.

### Added

- Tests, and releases published to PyPI from GitHub releases.
- The documentation split into `docs/`.

## 0.1.5 - 2026-08-04

### Changed

- `create_venv` deletes an existing environment and builds a new one. Pass
  `recreate=False` to reuse it.
