# pyeasydeploy

Deploy Python apps to Linux servers over SSH, with plain Python functions on top of [Fabric](https://www.fabfile.org/): no agents on the server, no YAML, no DSL to learn. Your deploy is a `deploy.py` in your project that reads top to bottom.

It is made for a few servers and a team that writes Python, not to compete with Ansible or Docker.

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

The full documentation is at https://offerrall.github.io/pyeasydeploy/.

## Documentation

- [Overview](https://offerrall.github.io/pyeasydeploy/): what a deploy does step by step, and what the server needs.
- [Guide](https://offerrall.github.io/pyeasydeploy/guide/): connecting, remote Python, venvs and packages, files and services.
- [Reference](https://offerrall.github.io/pyeasydeploy/reference/): every public name, its arguments and what it does.
- [Reproducibility](https://offerrall.github.io/pyeasydeploy/reproducibility/): what a deploy guarantees, what it does not, and orphan services.
- [Design](https://offerrall.github.io/pyeasydeploy/design/): the ideas behind it, and what it is not.

### Maintaining

- [Releasing](https://offerrall.github.io/pyeasydeploy/releasing/): the release workflow and the one-time PyPI setup.
