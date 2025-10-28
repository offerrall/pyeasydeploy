from typing import NamedTuple, Optional
from fabric import Connection

def connect_to_host(
    host: str, 
    user: str, 
    password: Optional[str] = None, 
    key_filename: Optional[str] = None,
    port: int = 22
) -> Connection:
    """
    Connect to a remote host via SSH.
    
    Args:
        host: Remote host address
        user: Username for SSH connection
        password: Password for authentication (optional)
        key_filename: Path to SSH private key file (optional)
        port: SSH port (default: 22)
    
    Returns:
        Fabric Connection object
    
    Raises:
        ValueError: If neither password nor key_filename is provided
    """
    if password is None and key_filename is None:
        raise ValueError("You must provide either 'password' or 'key_filename' for authentication")
    
    if password is not None and key_filename is not None:
        raise ValueError("Provide either 'password' or 'key_filename', not both")
    
    connect_kwargs = {}
    
    if password is not None:
        connect_kwargs["password"] = password
    elif key_filename is not None:
        connect_kwargs["key_filename"] = key_filename
    
    conn = Connection(
        host=host,
        user=user,
        port=port,
        connect_kwargs=connect_kwargs
    )
    
    if password is not None:
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