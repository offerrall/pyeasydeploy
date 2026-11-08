# Reproducibility

The goal: **after a deploy, the parts of the server the library owns are a function of your project, not of what was there before.** Run the same script twice, or against a fresh server, and the app runs the same code with the same packages.

What that covers:

- **The code.** Every deploy uploads the project to a new, empty release directory. Nothing is left over from an earlier deploy.
- **The packages.** `uv sync --frozen` installs exactly the versions in `uv.lock`, into a new virtual environment per release. Packages you stopped declaring are gone, and the server never resolves versions on its own.
- **The interpreter.** Python comes from uv, not from the distribution, so a system upgrade cannot change it. `"3.13"` follows 3.13's patch releases; `"3.13.9"` is fixed.
- **The service.** Its unit file is rewritten from the `App` on every deploy.

What it does **not** cover, on purpose:

- **uv and Python patch releases.** Without a `url`, `ensure_uv` takes the latest uv, and `"3.13"` the latest 3.13.x: two deploys a month apart may run different patch releases. Pin a full Python version and pass your own uv `url` to freeze both.
- **The rest of the server.** System packages, users, nginx, databases, firewall. The library does not touch them.
- **Files the app creates at runtime.** Databases, uploads, caches. Keep them outside `~/.pyeasydeploy/apps/`: a release directory is removed two deploys later, with whatever the app wrote into it.
- **Apps deployed by earlier runs.** `deploy_app` manages the app you hand it and nothing else.

## Limitation: orphan apps

There is no `prune`. If you rename an app, say `web` becomes `site`, the new one is deployed and started, and `web` **keeps running with its old code**. Same if you drop an app from your script: it is not removed, it just stops being deployed.

A prune that removed every app not in your script would take down apps deployed by other scripts to the same user. So removing an app is manual, through the escape hatch:

```python
from pyeasydeploy import fabric_connection

conn = fabric_connection(server)
conn.run('export XDG_RUNTIME_DIR="/run/user/$(id -u)"; systemctl --user disable --now pyeasydeploy-web.service')
conn.run("rm -rf ~/.pyeasydeploy/apps/web")
```
