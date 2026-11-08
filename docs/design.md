# Design

## The ideas behind it

**Linux is a bootstrap for Python.** The server provides the kernel, SSH and systemd; the deploy brings uv, Python and the app. Nothing depends on the distribution or its packages, and nothing needs sudo: the one step that needs root, enabling lingering, is done once by hand.

**Values and functions.** Every model is immutable and validated when built, and every step is a function that takes the value the previous one returned: `Server`, then `Uv`, then `Python`, then `Release`. The SSH connection is kept inside, one per `Server`, so a deploy script never holds an object that can be half-configured.

**One folder, and nothing outside it.** Everything the library creates lives in `~/.pyeasydeploy`, and every removal is checked to be strictly inside it, after normalizing the path: no list of forbidden paths to get wrong. The one thing outside is the link `systemctl --user enable` creates in `~/.config/systemd/user/`.

**Exact and up to date.** The app gets the exact versions of its `uv.lock`. uv and Python patch releases are kept current on every deploy, so security fixes arrive without maintenance; pin a full Python version, or pass your own uv `url`, to freeze them.

**Fail early, fail clearly.** A model with a relative path or an app name that would break a path fails on your machine. A project without `uv.lock`, or a user without lingering, fails before anything is uploaded, with the fix in the message.

**An escape hatch.** `fabric_connection(server)` gives the underlying Fabric connection, for anything the library does not do.

## What it is not

- **Not Ansible or Terraform.** No inventories, no state files, no declarative idempotency. Imperative on purpose.
- **Not Docker.** The isolation is a virtual environment per release and a Python per server folder, which is enough when everything is Python.
- **Not provisioning.** nginx, databases, firewalls and the rest of the server are up to you.
- **No secret management.** The passwords you pass in are your environment's responsibility.
- **No fleet orchestration.** One server per `Server`. For several, write a loop.
- **Linux targets with systemd, on `x86_64` or `aarch64`.** The machine you deploy from can be Windows, macOS or Linux.
