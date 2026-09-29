# Reproducibility

The goal: **after a deploy, the parts of the server the library owns are a function of your script, not of what was there before.** Run the same script twice, or run it against a fresh server, and you get the same result.

What that covers:

- **Uploads.** `upload_file` and `upload_directory` remove the destination first. The remote tree is exactly your local tree minus the ignored patterns. Add `mode=` and the permissions stop depending on the machine you deploy from too.
- **Venvs.** `create_venv` wipes and rebuilds by default. Packages you stopped declaring disappear, pinned versions really apply, and changing the target Python version actually changes the interpreter — none of which happens in a reused venv.
- **Services.** The `.conf` for a deployed service is rewritten from the `SupervisorService` model every time. What you declare is what supervisord reads.

What it does **not** cover — real gaps, not oversights:

- **System packages and OS state.** pacman/apt, users, nginx, databases, firewall, cron. Out of scope; the library doesn't touch them (the one exception is `install_supervisor`, because services are its job).
- **Files the app creates at runtime.** Databases, logs, uploads, caches. They live wherever your app puts them and survive every deploy — which is normally what you want. If one lands inside an upload destination, it gets wiped: keep runtime data outside deploy directories.
- **Services deployed by previous runs.** `deploy_supervisor_service` manages the service you hand it and nothing else. Services from earlier runs stay untouched, and stay running.

## Known limitation: orphan services

There is no `prune`. If you rename a service — say `myapp` becomes `myapp-web` — the new `.conf` is deployed and started, and the old `myapp` **keeps running with the old code**, from a venv you may have just rebuilt underneath it. Same if you drop a service from your script: it isn't removed, it just stops being managed.

A `deploy_supervisor_services(services, prune=True)` that deleted every `.conf` not declared would be the coherent thing to do, but on a host shared with other apps it would take down services this library never deployed. Too much blast radius for now. Until then, removing a service is manual:

```python
conn.sudo("supervisorctl stop myapp")
conn.sudo("rm /etc/supervisor/conf.d/myapp.conf")  # Debian/Ubuntu
# conn.sudo("rm /etc/supervisor.d/myapp.ini")      # Arch
conn.sudo("supervisorctl update")
```

