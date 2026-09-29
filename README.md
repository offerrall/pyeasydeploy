# pyeasydeploy

[![PyPI](https://img.shields.io/pypi/v/pyeasydeploy.svg)](https://pypi.org/project/pyeasydeploy/)

A small library for deploying Python applications to Linux servers over SSH. Plain Python functions on top of [Fabric](https://www.fabfile.org/): no agents on the server, no YAML, no DSL to learn. Your deploy script reads top to bottom.

It doesn't try to compete with Ansible or Docker. If you have a few servers, you write Python, and you want your deploy to be just another `deploy.py` in your project, it might be for you.

## A complete deploy

```python
from pyeasydeploy import (
    Host, Key, SupervisorService, connect, create_venv,
    deploy_supervisor_service, get_target_python_instance,
    install_local_package, supervisor_restart,
)

APP = "myapp"
USER = "deploy"

conn = connect(Host(
    address="203.0.113.10",
    user=USER,
    auth=Key(path="~/.ssh/id_ed25519"),
    sudo_password="...",   # better: os.environ["SUDO_PASSWORD"]
))

py = get_target_python_instance(conn, "3.11")
venv = create_venv(conn, py, f"/home/{USER}/venvs/{APP}")
install_local_package(conn, venv, f"./{APP}")

deploy_supervisor_service(conn, SupervisorService(
    name=APP,
    command=f"{venv.path}/bin/python -m {APP}",
    directory=f"/home/{USER}",
    user=USER,
))
supervisor_restart(conn, APP)
```

Connect, pick an interpreter, create the venv, install your package with its dependencies, and leave it running as a supervised service that survives reboots. The `venv` object returned by `create_venv` carries its own path: the service command is built from it, no paths repeated by hand.

## Installation

```bash
pip install pyeasydeploy
```

Python ≥ 3.11 on your machine. On the server: SSH and some `python3` (tested on Arch, Debian and Ubuntu).

## Documentation

- [Guide](docs/guide.md): connecting, remote Python, venvs and packages, files and services.
- [Reproducibility](docs/reproducibility.md): what a deploy guarantees, and what it does not.
- [Design](docs/design.md): the ideas behind it, and what it is not.
- [Changelog](CHANGELOG.md)
- [Releasing](RELEASING.md)

## License

MIT
