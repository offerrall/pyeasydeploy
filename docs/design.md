# Design

## The ideas behind it

**Destructive and reproducible.** Uploads remove the destination and copy from scratch, every time; venvs are recreated, not reused. After each deploy, the server has exactly what your script says it should have — no leftovers from previous versions. (The one safety net: paths like `/`, `/home` or `/etc` are rejected before anything is removed.) See [Reproducibility](reproducibility.md) for how far that guarantee reaches.

**Fail early, fail clearly.** Models validate on construction: a relative path or a service name that would corrupt the INI file blows up on your laptop with a useful message, before touching the server. Functions that need sudo check for it upfront — an immediate error with instructions, instead of the classic hang waiting for a password that will never come.

**Trust the user.** The library validates *form* (types, absolute paths, dangerous characters), not your *facts*: if you hand-build a `PythonInstance` pointing at an exotic interpreter, it's accepted. You know what's on your server.

## What it is not

- **Not Ansible/Terraform.** No inventories, no state, no declarative idempotency. Imperative on purpose.
- **Not provisioning.** It installs supervisor because services are its job, and that's where it stops: nginx, databases and the rest of your server are up to you.
- **No secret management.** The passwords you pass in are your environment's responsibility.
- **No fleet orchestration.** One connection, one server. For several, write a loop.
- **Linux targets only.** The source machine can be Windows, macOS or Linux.

For many of those cases, bigger tools will do it better. This one exists for when you don't need them.
