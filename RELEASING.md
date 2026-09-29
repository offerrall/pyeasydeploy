# Releasing

[Back to README](README.md)

`.github/workflows/build.yml` runs the tests on Linux and Windows with Python 3.11 to 3.14
on pushes to `main` (except documentation-only changes), on manual runs and on published
GitHub releases. For a release it also checks that the tag is `v` plus the version, builds
the package, tests the built wheel and, only if all that passed, uploads it to PyPI.

1. Set `__version__` in `pyeasydeploy/__init__.py` and add its entry to `CHANGELOG.md`.
2. Commit and push to `main`.
3. Publish a GitHub release tagged `v` plus that version:
   `gh release create v1.0.0 --title v1.0.0 --notes-file <notes>`.

A version that reached PyPI cannot be uploaded again: if something is wrong with it,
release the next patch version.

One-time setup: on PyPI, add a Trusted Publisher to the `pyeasydeploy` project with owner
`offerrall`, repository `pyeasydeploy`, workflow `build.yml` and environment
`pypi-release`. No API token is needed.
