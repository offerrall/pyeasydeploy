# Changelog

## 1.0.2

### Added

- The `LICENSE` file with the MIT text that `pyproject.toml` declares, shipped in
  the package. The code is the same as 1.0.1.

## 1.0.1

### Changed

- `pytypehint` is pinned to the exact version this release is tested with,
  `==1.2.1`, instead of `>=1.2`: a new pytypehint can no longer change what an
  installed pyeasydeploy does. The code is the same as 1.0.0.

## 1.0.0

The models are rebuilt on [pytypehint](https://github.com/offerrall/pytypehint): deeply
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
