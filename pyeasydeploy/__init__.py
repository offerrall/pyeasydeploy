from typing import NamedTuple
from fabric import Connection

class RemoteHost(NamedTuple):
    host: str
    user: str
    password: str
    port: int = 22
    
    def connect(self) -> Connection:
        conn = Connection(
            host=self.host,
            user=self.user,
            port=self.port,
            connect_kwargs={"password": self.password}
        )
        conn.config.sudo.password = self.password
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