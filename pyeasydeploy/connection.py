from fabric import Connection

from .models import Host, Password


def connect(host: Host) -> Connection:
    """An SSH connection to host. It is lazy: a wrong password shows up on the first command."""
    if isinstance(host.auth, Password):
        connect_kwargs = {"password": host.auth.value}
    else:
        connect_kwargs = {"key_filename": host.auth.path}
    conn = Connection(host=host.address, user=host.user, port=host.port,
                      connect_kwargs=connect_kwargs)

    sudo_password = host.sudo_password
    if sudo_password is None and isinstance(host.auth, Password):
        sudo_password = host.auth.value
    if sudo_password is not None:
        conn.config.sudo.password = sudo_password
    return conn


def has_sudo_password(conn: Connection) -> bool:
    return bool(getattr(conn.config.sudo, "password", None))


def require_sudo(conn: Connection, what: str = "this operation") -> None:
    """Raise PermissionError now if sudo would hang waiting for a password."""
    if has_sudo_password(conn):
        return
    raise PermissionError(
        f"{what} requires sudo, but no sudo password is configured for this connection. "
        "Give the Host a sudo_password, or authenticate with a Password."
    )
