"""SSH connection factory for pyeasydeploy.

Builds Fabric Connection objects with authentication and sudo correctly
wired. Depends only on models-level philosophy (validate at the
boundary); imports nothing from the rest of the package.
"""

from typing import Optional

from fabric import Connection


def connect_to_host(
    host: str,
    user: str,
    password: Optional[str] = None,
    key_filename: Optional[str] = None,
    sudo_password: Optional[str] = None,
    port: int = 22,
) -> Connection:
    """Create an SSH connection to a remote host.

    Exactly one of ``password`` or ``key_filename`` must be provided
    for SSH authentication.

    Sudo is configured independently: if ``sudo_password`` is given it
    is used for ``conn.sudo()`` calls; otherwise, if ``password`` is
    given it is reused for sudo (the common case where the SSH user's
    password is also the sudo password). With key-based auth and no
    ``sudo_password``, any later ``conn.sudo()`` call would block
    forever waiting for a password prompt — so functions in this
    library that need sudo will refuse early instead (see
    ``require_sudo``).

    Note: the connection is lazy. Fabric does not open the SSH session
    here; authentication errors surface on the first command run.

    Args:
        host: Remote host address (IP or hostname).
        user: Username for the SSH connection.
        password: Password for SSH authentication. Mutually exclusive
            with key_filename.
        key_filename: Path to an SSH private key file. Mutually
            exclusive with password.
        sudo_password: Password for sudo on the remote host. Defaults
            to ``password`` when that is provided. Required later by
            any sudo-using function when authenticating with a key
            (unless the remote user has passwordless sudo configured,
            in which case sudo works without it).
        port: SSH port. Defaults to 22.

    Returns:
        A Fabric Connection, with sudo password configured when
        available.

    Raises:
        TypeError: If any argument has the wrong type.
        ValueError: If host or user are empty, both or neither of
            password/key_filename are provided, or port is outside
            1-65535.
    """
    if not isinstance(host, str):
        raise TypeError(f"host must be str, got {type(host).__name__}")
    if not host.strip():
        raise ValueError("host must be a non-empty string")
    if not isinstance(user, str):
        raise TypeError(f"user must be str, got {type(user).__name__}")
    if not user.strip():
        raise ValueError("user must be a non-empty string")
    for name, value in (
        ("password", password),
        ("key_filename", key_filename),
        ("sudo_password", sudo_password),
    ):
        if value is not None and not isinstance(value, str):
            raise TypeError(f"{name} must be str or None, got {type(value).__name__}")
    if isinstance(port, bool) or not isinstance(port, int):
        raise TypeError(f"port must be int, got {type(port).__name__}")
    if not 1 <= port <= 65535:
        raise ValueError(f"port must be in 1-65535, got {port}")

    if password is None and key_filename is None:
        raise ValueError(
            "You must provide either 'password' or 'key_filename' "
            "for authentication"
        )
    if password is not None and key_filename is not None:
        raise ValueError("Provide either 'password' or 'key_filename', not both")

    connect_kwargs = {}
    if password is not None:
        connect_kwargs["password"] = password
    else:
        connect_kwargs["key_filename"] = key_filename

    conn = Connection(
        host=host,
        user=user,
        port=port,
        connect_kwargs=connect_kwargs,
    )

    effective_sudo = sudo_password if sudo_password is not None else password
    if effective_sudo is not None:
        conn.config.sudo.password = effective_sudo

    return conn


def has_sudo_password(conn: Connection) -> bool:
    """Return True if a sudo password is configured on this connection.

    Args:
        conn: Connection created by connect_to_host (or any Fabric
            Connection).

    Returns:
        True when conn.config.sudo.password is set to a non-empty value.
    """
    return bool(getattr(conn.config.sudo, "password", None))


def require_sudo(conn: Connection, what: str = "this operation") -> None:
    """Fail fast if the connection cannot run sudo non-interactively.

    Call this at the top of any function that uses ``conn.sudo()``.
    Turns the silent infinite hang (sudo waiting for a password that
    will never arrive) into an immediate, explanatory error.

    Note: a remote user with passwordless sudo (NOPASSWD in sudoers)
    does not need a sudo password; pass an empty-string check bypass by
    configuring ``sudo_password=""`` is NOT supported — instead, this
    check is advisory: it only raises when no password is configured
    AND the connection was key-authenticated, the exact combination
    that hangs.

    Args:
        conn: Connection to check.
        what: Human description of the operation, used in the error
            message.

    Raises:
        PermissionError: If no sudo password is configured and the
            connection has no SSH password to fall back on.
    """
    if has_sudo_password(conn):
        return
    raise PermissionError(
        f"{what} requires sudo, but no sudo password is configured for "
        f"this connection. Pass sudo_password= to connect_to_host(), or "
        f"configure passwordless sudo (NOPASSWD) for the remote user and "
        f"call the function with check_sudo=False if it offers it."
    )