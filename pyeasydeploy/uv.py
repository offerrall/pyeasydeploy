import hashlib
import io
import shlex
import tarfile
import urllib.request

from .connection import fabric_connection
from .models import Server, Uv
from .server import pyeasydeploy_dir


def latest_uv_version() -> str:
    request = urllib.request.Request("https://github.com/astral-sh/uv/releases/latest", method="HEAD")
    return urllib.request.urlopen(request).geturl().rsplit("/", 1)[-1]


def uv_url(arch: str, version: str) -> str:
    if arch not in ("x86_64", "aarch64"):
        raise ValueError(f"Unsupported architecture: {arch}")
    return f"https://github.com/astral-sh/uv/releases/download/{version}/uv-{arch}-unknown-linux-musl.tar.gz"


def uv_binary(url: str) -> bytes:
    data = urllib.request.urlopen(url).read()
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            if member.isfile() and member.name.rsplit("/", 1)[-1] == "uv":
                return tar.extractfile(member).read()
    raise RuntimeError(f"No uv binary inside {url}")


def ensure_uv(server: Server, url: str | None = None) -> Uv:
    conn = fabric_connection(server)
    directory = f"{pyeasydeploy_dir(server)}/bin"
    uv = Uv(server=server, path=f"{directory}/uv")
    path = shlex.quote(uv.path)

    if url is None:
        version = latest_uv_version()
        *installed, arch = conn.run(f"{path} --version; uname -m", hide=True, warn=True).stdout.splitlines()
        if installed and installed[0].split()[1:2] == [version]:
            return uv
        url = uv_url(arch.strip(), version)

    binary = uv_binary(url)
    expected = hashlib.sha256(binary).hexdigest()
    remote = conn.run(f"mkdir -p {shlex.quote(directory)} && sha256sum {path}",
                      hide=True, warn=True).stdout.split()
    if remote[:1] != [expected]:
        temp = shlex.quote(f"{uv.path}.tmp")
        conn.put(io.BytesIO(binary), f"{uv.path}.tmp")
        conn.run(f"chmod 755 {temp} && mv {temp} {path}", hide=True)
    return uv
