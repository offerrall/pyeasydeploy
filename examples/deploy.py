from pathlib import Path

from pyeasydeploy import App, Key, Server, app_logs, deploy_app, ensure_python, ensure_uv

server = Server(address="203.0.113.10", user="deploy", auth=Key(path="~/.ssh/id_ed25519"))
python = ensure_python(ensure_uv(server), "3.13")
deploy_app(python, App(name="demoapp", source=str(Path(__file__).parent / "demoapp"), command="demoapp"))
print(app_logs(server, "demoapp"))
