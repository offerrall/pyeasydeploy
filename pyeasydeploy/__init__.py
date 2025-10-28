from typing import NamedTuple
from fabric import Connection

def connect_to_host(host: str, user: str, password: str, port: int = 22) -> Connection:
    conn = Connection(
        host=host,
        user=user,
        port=port,
        connect_kwargs={"password": password}
    )
    conn.config.sudo.password = password
    return conn

class PythonInstance(NamedTuple):
    version: str
    executable: str

class VenvPython(NamedTuple):
    venv_name: str
    python_instance: PythonInstance
    venv_path: str

from .packages import *
from .python import *
from .venv import *
from .transfer import *
from .supervisor import *