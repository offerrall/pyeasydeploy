# pyeasydeploy

Deploy a Python app to a Linux server with a few lines of Python and no sudo. The server only needs SSH and systemd: the deploy brings everything else.

```python
from pyeasydeploy import App, Key, Server, deploy_app, ensure_python, ensure_uv

server = Server(address="203.0.113.10", user="deploy", auth=Key(path="~/.ssh/id_ed25519"))
python = ensure_python(ensure_uv(server), "3.13")
deploy_app(python, App(name="web", source="./web", command="web"))
```

That is the whole deploy, and it:

- **Brings its own Python.** It uploads [uv](https://docs.astral.sh/uv/), which installs the Python you ask for. The distribution, its packages and its Python never matter.
- **Installs exactly your `uv.lock`.** The server never picks versions on its own.
- **Keeps the app running while it installs.** Each deploy is a new release, switched to with one restart. A failed install leaves the running one untouched.
- **Runs it as a service.** systemd keeps it alive and starts it at boot. Its output goes to the journal, which rotates on its own.
- **Stays in its folder.** Everything lives in `~/.pyeasydeploy`, and nothing outside it is ever removed.

Immutable values and plain functions on top of [Fabric](https://www.fabfile.org/), made for a few servers and a team that writes Python.

The full documentation is at https://offerrall.github.io/pyeasydeploy/.

## Documentation

- [Overview](https://offerrall.github.io/pyeasydeploy/)
- [Guide](https://offerrall.github.io/pyeasydeploy/guide/)
- [Reference](https://offerrall.github.io/pyeasydeploy/reference/)
- [Reproducibility](https://offerrall.github.io/pyeasydeploy/reproducibility/)
- [Design](https://offerrall.github.io/pyeasydeploy/design/)
- [Releasing](https://offerrall.github.io/pyeasydeploy/releasing/)
