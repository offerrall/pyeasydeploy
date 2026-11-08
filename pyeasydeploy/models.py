from typing import Annotated

from pytypehint import Max, Min, Pattern, immutable

Text = Annotated[str, Pattern(r"(?s).*\S.*", message="must not be blank")]
Word = Annotated[str, Pattern(r"\S+", message="must be one word, without whitespace")]
RemotePath = Annotated[str, Pattern(r"/.*", message="must be an absolute path (start with '/')")]
NAME = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
Line = Annotated[str, Pattern(r"[^\n]*", message="must be one line")]
EnvName = Annotated[str, Pattern(r"[A-Za-z_][A-Za-z0-9_]*", message="must be a variable name, like NTFY_TOPIC")]


@immutable
class Password:
    value: Annotated[str, Min(1)]


@immutable
class Key:
    path: Text


@immutable
class Server:
    address: Word
    user: Word
    auth: Password | Key
    port: Annotated[int, Min(1), Max(65535)] = 22


@immutable
class Uv:
    server: Server
    path: RemotePath


@immutable
class Python:
    uv: Uv
    version: Annotated[str, Pattern(r"\d+(\.\d+)*", message="must look like '3.13' or '3.13.9'")]
    path: RemotePath


@immutable
class App:
    name: Annotated[str, Pattern(NAME, message="must be letters, digits, '_', '.' or '-'")]
    source: Text
    command: Annotated[str, Pattern(r"[^\n]*\S[^\n]*", message="must be one non-blank line")]
    package: Word | None = None
    environment: tuple[tuple[EnvName, Line], ...] = ()


@immutable
class Release:
    python: Python
    app: App
    path: RemotePath
