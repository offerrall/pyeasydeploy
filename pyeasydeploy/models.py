"""Shared data models for pyeasydeploy.

This module is the foundation layer: it imports nothing from the rest of
the package, so every other module can depend on it without cycles.

All models are frozen (immutable) and validate themselves on
construction: wrong types raise TypeError, invalid values raise
ValueError. Validation is structural only — it protects the integrity
of what we generate (paths that must be absolute to work remotely, INI
section headers that must parse) and never restricts which supervisord
features you can use.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Optional, Union

# ----------------------------------------------------------------------
# Private validation helpers (shared by all models)
# ----------------------------------------------------------------------


def _check_str(field_name: str, value: object) -> str:
    """Require a non-empty, non-blank str. Returns the value."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be str, got {type(value).__name__}")
    if not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _check_abs_posix_path(field_name: str, value: object) -> str:
    """Require a non-empty str that is an absolute POSIX path (remote
    hosts are Linux: paths must start with '/')."""
    _check_str(field_name, value)
    assert isinstance(value, str)
    if not value.startswith("/"):
        raise ValueError(
            f"{field_name} must be an absolute POSIX path (start with '/'), "
            f"got {value!r}"
        )
    return value


def _check_bool(field_name: str, value: object) -> bool:
    """Require a real bool (bool is a subclass of int, so a plain
    isinstance(int) check would let 0/1 through)."""
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be bool, got {type(value).__name__}")
    return value


# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class PythonInstance:
    """A Python interpreter found on the remote host.

    Attributes:
        version: Interpreter version string, e.g. "3.11". Must start
            with a digit.
        executable: Absolute remote path to the interpreter,
            e.g. "/usr/bin/python3.11".

    Raises:
        TypeError: On construction, if any field has the wrong type.
        ValueError: On construction, if version is empty or does not
            start with a digit, or executable is not an absolute path.
    """

    version: str
    executable: str

    def __post_init__(self) -> None:
        _check_str("version", self.version)
        if not self.version[0].isdigit():
            raise ValueError(
                f"version must start with a digit, got {self.version!r}"
            )
        _check_abs_posix_path("executable", self.executable)


@dataclass(frozen=True)
class VenvPython:
    """A virtual environment on the remote host, bound to the interpreter
    that created it.

    Attributes:
        venv_name: Name of the environment, usually the last component
            of venv_path. No whitespace or "/" allowed.
        python_instance: Interpreter used to create this environment.
        venv_path: Absolute remote path to the environment,
            e.g. "/home/app/venvs/myapp".

    Raises:
        TypeError: On construction, if any field has the wrong type.
        ValueError: On construction, if venv_name contains whitespace
            or "/", or venv_path is not an absolute path.
    """

    venv_name: str
    python_instance: PythonInstance
    venv_path: str

    def __post_init__(self) -> None:
        _check_str("venv_name", self.venv_name)
        if "/" in self.venv_name or any(c.isspace() for c in self.venv_name):
            raise ValueError(
                f"venv_name must not contain '/' or whitespace, "
                f"got {self.venv_name!r}"
            )
        if not isinstance(self.python_instance, PythonInstance):
            raise TypeError(
                "python_instance must be a PythonInstance, got "
                f"{type(self.python_instance).__name__}"
            )
        _check_abs_posix_path("venv_path", self.venv_path)


@dataclass(frozen=True)
class SupervisorService:
    """Description of a supervisord [program:x] entry.

    Named fields cover the common options; the open `extra` mapping
    accepts ANY other supervisord program option verbatim, so no
    supervisord feature is out of reach. Values may be str, int or
    bool (bools are rendered as "true"/"false").

    Example with rotating logs and process priority::

        SupervisorService(
            name="myapp",
            command="/home/app/venv/bin/python -m myapp",
            extra={
                "stdout_logfile_maxbytes": "10MB",
                "stdout_logfile_backups": 5,
                "stderr_logfile_maxbytes": "10MB",
                "stderr_logfile_backups": 5,
                "priority": 200,
                "stopsignal": "INT",
            },
        )

    Attributes:
        name: Program name; becomes the [program:<name>] section header.
            Must be non-empty, with no whitespace and no "]".
        command: Command line supervisord runs,
            e.g. "/home/app/venv/bin/python -m myapp".
        directory: Remote working directory the process is started from.
            None omits the line (supervisord default applies).
        user: Unix user the process runs as. None omits the line
            (process runs as supervisord's own user).
        autostart: Start the program automatically when supervisord
            starts. Defaults to True.
        autorestart: Restart the program automatically if it exits.
            Defaults to True.
        stdout_logfile: stdout log destination. Any value supervisord
            accepts: an absolute path, "AUTO", "NONE" or "syslog".
            None omits the line (supervisord defaults to AUTO).
            "%(program_name)s" is expanded by supervisord itself.
        stderr_logfile: stderr log destination. Same rules as
            stdout_logfile.
        environment: Environment variables in supervisord syntax,
            e.g. 'KEY="value",OTHER="x"'. None omits the line.
        extra: Any additional [program:x] options, rendered verbatim
            as key=value lines. Keys must not collide with the named
            fields above (that would emit duplicate INI keys).

    Raises:
        TypeError: On construction, if any field has the wrong type.
        ValueError: On construction, if name would corrupt the INI
            section header (empty, whitespace or "]"), or an extra key
            collides with a named field, or an extra key is empty or
            contains characters that would break a key=value INI line.
    """

    name: str
    command: str
    directory: Optional[str] = None
    user: Optional[str] = None
    autostart: bool = True
    autorestart: bool = True
    stdout_logfile: Optional[str] = "/var/log/supervisor/%(program_name)s.log"
    stderr_logfile: Optional[str] = "/var/log/supervisor/%(program_name)s_err.log"
    environment: Optional[str] = None
    extra: Mapping[str, Union[str, int, bool]] = field(default_factory=dict)

    # Named fields that render as their own INI lines; extra keys must
    # not shadow them.
    _NAMED_KEYS = frozenset(
        {
            "command", "directory", "user", "autostart", "autorestart",
            "stdout_logfile", "stderr_logfile", "environment",
        }
    )

    def __post_init__(self) -> None:
        _check_str("name", self.name)
        if any(c.isspace() for c in self.name) or "]" in self.name:
            raise ValueError(
                f"Invalid service name {self.name!r}: no whitespace or ']' "
                "allowed (it would corrupt the INI section header)"
            )
        _check_str("command", self.command)
        for opt in ("directory", "user", "stdout_logfile",
                    "stderr_logfile", "environment"):
            value = getattr(self, opt)
            if value is not None:
                _check_str(opt, value)
        _check_bool("autostart", self.autostart)
        _check_bool("autorestart", self.autorestart)

        if not isinstance(self.extra, Mapping):
            raise TypeError(
                f"extra must be a mapping, got {type(self.extra).__name__}"
            )
        for key, value in self.extra.items():
            _check_str("extra key", key)
            if key in self._NAMED_KEYS:
                raise ValueError(
                    f"extra key {key!r} collides with the named field "
                    f"'{key}'; set it through the field instead"
                )
            if "=" in key or "\n" in key or any(c.isspace() for c in key):
                raise ValueError(
                    f"extra key {key!r} would break the key=value INI line"
                )
            if not isinstance(value, (str, int, bool)):
                raise TypeError(
                    f"extra[{key!r}] must be str, int or bool, "
                    f"got {type(value).__name__}"
                )
            if isinstance(value, str) and "\n" in value:
                raise ValueError(
                    f"extra[{key!r}] must not contain newlines"
                )
        # Freeze the mapping so the dataclass is deeply immutable.
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))