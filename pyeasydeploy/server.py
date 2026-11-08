from .connection import fabric_connection
from .models import Server

_homes: dict[Server, str] = {}


def server_arch(server: Server) -> str:
    return fabric_connection(server).run("uname -m", hide=True).stdout.strip()


def pyeasydeploy_dir(server: Server) -> str:
    if server not in _homes:
        _homes[server] = fabric_connection(server).run("echo $HOME", hide=True).stdout.strip()
    return f"{_homes[server]}/.pyeasydeploy"
