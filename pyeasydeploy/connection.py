import os

from fabric import Connection

from .models import Password, Server

_connections: dict[Server, Connection] = {}


def fabric_connection(server: Server) -> Connection:
    if server not in _connections:
        if isinstance(server.auth, Password):
            connect_kwargs = {"password": server.auth.value}
        else:
            connect_kwargs = {"key_filename": os.path.expanduser(server.auth.path)}
        _connections[server] = Connection(host=server.address, user=server.user,
                                          port=server.port, connect_kwargs=connect_kwargs)
    return _connections[server]
