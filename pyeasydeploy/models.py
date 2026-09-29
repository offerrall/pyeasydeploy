"""Deeply immutable models that validate themselves on construction, built with pytypehint.

The types describe structure only: what the library generates must be valid (absolute
remote paths, INI lines that parse), never which supervisord features you may use.
All models take keyword arguments. This module imports nothing from the package.
"""

from typing import Annotated

from pytypehint import Max, Min, Pattern, immutable

Text = Annotated[str, Pattern(r"(?s).*\S.*", message="must not be blank")]
Word = Annotated[str, Pattern(r"\S+", message="must be one word, without whitespace")]
RemotePath = Annotated[str, Pattern(r"/.*", message="must be an absolute path (start with '/')")]


@immutable
class Password:
    value: Annotated[str, Min(1)]


@immutable
class Key:
    """An SSH private key file on this machine, e.g. Key(path="~/.ssh/id_ed25519")."""

    path: Text


@immutable
class Host:
    """A server to deploy to.

    sudo uses sudo_password, or the SSH password when auth is a Password. With a Key and
    no sudo_password, the functions that need sudo refuse early instead of hanging.
    """

    address: Word
    user: Word
    auth: Password | Key
    sudo_password: str | None = None
    port: Annotated[int, Min(1), Max(65535)] = 22


@immutable
class PythonInstance:
    """An interpreter on the server, e.g. PythonInstance(version="3.11", executable="/usr/bin/python3.11")."""

    version: Annotated[str, Pattern(r"\d+(\.\d+)*", message="must look like '3' or '3.11'")]
    executable: RemotePath


@immutable
class Venv:
    """A virtual environment on the server, bound to the interpreter that created it."""

    python: PythonInstance
    path: RemotePath


@immutable
class Option:
    """One supervisord program option, written as key=value."""

    key: Annotated[str, Pattern(r"[^\s=]+", message="must have no whitespace or '='")]
    value: Annotated[str, Pattern(r"[^\n]*", message="must be one line")] | int | bool


_NAMED_OPTIONS = frozenset({
    "command", "directory", "user", "autostart", "autorestart",
    "stdout_logfile", "stderr_logfile", "environment",
})


@immutable
class SupervisorService:
    """A supervisord [program:name] entry.

    None fields are left out of the file, so supervisord's defaults apply. `extra` takes
    any other option (bools render as true/false), so no supervisord feature is out of
    reach; its keys must not repeat a named field or each other.
    """

    name: Annotated[str, Pattern(r"[^\s\]]+", message="must have no whitespace or ']'")]
    command: Text
    directory: RemotePath | None = None
    user: Word | None = None
    autostart: bool = True
    autorestart: bool = True
    stdout_logfile: Text | None = "/var/log/supervisor/%(program_name)s.log"
    stderr_logfile: Text | None = "/var/log/supervisor/%(program_name)s_err.log"
    environment: Text | None = None
    extra: tuple[Option, ...] = ()

    def __post_init__(self) -> None:
        keys = [option.key for option in self.extra]
        for key in keys:
            if key in _NAMED_OPTIONS:
                raise ValueError(f"extra: {key!r} is a named field; set it through the field")
        repeated = sorted({key for key in keys if keys.count(key) > 1})
        if repeated:
            raise ValueError(f"extra: {', '.join(map(repr, repeated))} given more than once")
