import io
import subprocess
import sys
import tarfile

import pytest

import pyeasydeploy as p
from pyeasydeploy import app as app_module
from pyeasydeploy import connection, server as server_module, uv as uv_module
from pyeasydeploy.paths import inside, remove_command

SERVER = p.Server(address="h", user="u", auth=p.Key(path="~/.ssh/k"))
BASE = "/home/u/.pyeasydeploy"
UV = p.Uv(server=SERVER, path=f"{BASE}/bin/uv")
PYTHON = p.Python(uv=UV, version="3.13.9", path=f"{BASE}/python/cpython-3.13.9/bin/python3.13")


class Result:
    def __init__(self, stdout=""):
        self.stdout = stdout


class FakeConn:
    """Records what would reach the server; answers a command by a substring of it."""

    def __init__(self, responses=None):
        self.responses = {"echo $HOME": "/home/u", **(responses or {})}
        self.calls = []

    def run(self, cmd, **kw):
        self.calls.append(("run", cmd))
        return Result(next((out for key, out in self.responses.items() if key in cmd), ""))

    def put(self, local, remote):
        self.calls.append(("put", local.getvalue(), remote))

    def commands(self):
        return [call[1] for call in self.calls if call[0] == "run"]

    def puts(self):
        return {call[2]: call[1] for call in self.calls if call[0] == "put"}


@pytest.fixture
def fake(monkeypatch):
    def install(responses=None):
        conn = FakeConn(responses)
        monkeypatch.setitem(connection._connections, SERVER, conn)
        monkeypatch.setattr(server_module, "_homes", {})
        return conn
    return install


@pytest.fixture
def project(tmp_path):
    (tmp_path / "uv.lock").write_text('version = 1\n\n[[package]]\nname = "web"\nsource = { editable = "." }\n')
    (tmp_path / "pyproject.toml").write_text("[project]")
    (tmp_path / "web.py").write_text("print('hi')")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "web.pyc").write_bytes(b"")
    (tmp_path / "local.db").write_bytes(b"")
    return tmp_path


# Models

def test_models_accept_valid_values():
    assert SERVER.port == 22
    assert p.App(name="web", source="./web", command="python -m web").package is None


@pytest.mark.parametrize("build", [
    lambda: p.Server(address="a b", user="u", auth=p.Password(value="p")),
    lambda: p.Server(address="h", user="u", auth="pw"),
    lambda: p.Server(address="h", user="u", auth=p.Password(value="p"), port=0),
    lambda: p.Server(address="h", user="u", auth=p.Password(value="")),
    lambda: p.Uv(server=SERVER, path="bin/uv"),
    lambda: p.Python(uv=UV, version="v3", path="/x/python"),
    lambda: p.App(name="my app", source="./web", command="web"),
    lambda: p.App(name="../web", source="./web", command="web"),
    lambda: p.App(name="web", source="./web", command="web\nrm -rf /"),
    lambda: p.App(name="web", source=" ", command="web"),
    lambda: p.App(name="web", source=".", command="web", environment=(("BAD NAME", "x"),)),
    lambda: p.App(name="web", source=".", command="web", environment=(("KEY", "two\nlines"),)),
])
def test_models_reject_invalid_values(build):
    with pytest.raises((TypeError, ValueError)):
        build()


def test_equal_servers_share_one_connection():
    twin = p.Server(address="h2", user="u", auth=p.Key(path="~/.ssh/k"))
    again = p.Server(address="h2", user="u", auth=p.Key(path="~/.ssh/k"))
    try:
        assert p.fabric_connection(twin) is p.fabric_connection(again)
    finally:
        connection._connections.pop(twin, None)


# Paths

@pytest.mark.parametrize("path", [
    f"{BASE}/apps/web",
    f"{BASE}/apps/web/releases/1/",
])
def test_inside_accepts_paths_under_the_base(path):
    assert inside(BASE, path) == path.rstrip("/")


@pytest.mark.parametrize("path", [
    BASE,
    f"{BASE}/../etc",
    f"{BASE}/apps/../../x",
    f"/{BASE}/apps",
    "/home/u",
    "/",
])
def test_inside_refuses_anything_else(path):
    with pytest.raises(ValueError):
        inside(BASE, path)


@pytest.mark.skipif(sys.platform == "win32", reason="runs a POSIX shell")
def test_remove_refuses_to_follow_a_symlink_out_of_the_base(tmp_path):
    base, outside = tmp_path / "base", tmp_path / "outside"
    (base / "apps" / "web").mkdir(parents=True)
    (outside / "old").mkdir(parents=True)
    (base / "apps" / "web" / "releases").symlink_to(outside)
    command = remove_command(str(base), f"{base}/apps/web/releases/old")
    result = subprocess.run(["sh", "-c", command], capture_output=True, text=True)
    assert result.returncode == 1 and "resolves outside" in result.stderr
    assert (outside / "old").is_dir()


@pytest.mark.skipif(sys.platform == "win32", reason="runs a POSIX shell")
def test_remove_removes_inside_the_base(tmp_path):
    (tmp_path / "apps" / "web" / "releases" / "old").mkdir(parents=True)
    (tmp_path / "apps" / "web" / "releases" / "keep").mkdir()
    command = remove_command(str(tmp_path), f"{tmp_path}/apps/web/releases/old", f"{tmp_path}/apps/web/x.tar.gz")
    subprocess.run(["sh", "-c", command], check=True)
    assert sorted(path.name for path in (tmp_path / "apps/web/releases").iterdir()) == ["keep"]


# uv

def test_uv_url_by_architecture():
    assert uv_module.uv_url("aarch64", "0.13.7") == (
        "https://github.com/astral-sh/uv/releases/download/0.13.7/uv-aarch64-unknown-linux-musl.tar.gz")
    with pytest.raises(ValueError):
        uv_module.uv_url("armv7l", "0.13.7")


def test_uv_binary_takes_the_uv_file_from_a_tarball(tmp_path):
    tarball = tmp_path / "uv.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        for name, content in [("uv-x/uvx", b"no"), ("uv-x/uv", b"binary")]:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    assert uv_module.uv_binary(tarball.as_uri()) == b"binary"


def test_ensure_uv_skips_the_download_when_the_server_has_the_latest(fake, monkeypatch):
    conn = fake({"uv --version": "uv 0.13.7 (abc 2026-11-03)\nx86_64"})
    monkeypatch.setattr(uv_module, "latest_uv_version", lambda: "0.13.7")
    monkeypatch.setattr(uv_module, "uv_binary", lambda url: pytest.fail("downloaded"))
    assert p.ensure_uv(SERVER) == UV
    assert conn.puts() == {}


def test_ensure_uv_uploads_when_the_server_is_behind(fake, monkeypatch):
    conn = fake({"uv --version": "uv 0.12.0\nx86_64"})
    monkeypatch.setattr(uv_module, "latest_uv_version", lambda: "0.13.7")
    urls = []
    monkeypatch.setattr(uv_module, "uv_binary", lambda url: urls.append(url) or b"binary")
    p.ensure_uv(SERVER)
    assert urls == [uv_module.uv_url("x86_64", "0.13.7")]
    assert conn.puts() == {f"{UV.path}.tmp": b"binary"}
    assert any(cmd.startswith("chmod 755") and cmd.endswith(f"mv {UV.path}.tmp {UV.path}")
               for cmd in conn.commands())


def test_ensure_uv_with_a_url_compares_hashes(fake, monkeypatch):
    import hashlib
    conn = fake({"sha256sum": hashlib.sha256(b"binary").hexdigest() + "  uv"})
    monkeypatch.setattr(uv_module, "uv_binary", lambda url: b"binary")
    p.ensure_uv(SERVER, url="file:///my/uv.tar.gz")
    assert conn.puts() == {}


# Python

def test_ensure_python_installs_into_the_pyeasydeploy_dir(fake):
    conn = fake({"python install": f"{PYTHON.path}\n3.13.9"})
    assert p.ensure_python(UV, "3.13") == PYTHON
    install = conn.commands()[0]
    assert f"UV_PYTHON_INSTALL_DIR={BASE}/python" in install
    assert "python install --upgrade --no-bin 3.13" in install


def test_ensure_python_keeps_an_exact_version(fake):
    conn = fake({"python install": f"{PYTHON.path}\n3.13.9"})
    p.ensure_python(UV, "3.13.9")
    assert "python install --no-bin 3.13.9" in conn.commands()[0]


# Apps

@pytest.mark.parametrize("control", [p.app_status, p.app_logs, p.restart_app, p.stop_app])
def test_controls_refuse_a_name_that_is_not_one(fake, control):
    conn = fake()
    with pytest.raises(ValueError, match="Invalid app name"):
        control(SERVER, "web; touch /tmp/mark; #")
    assert conn.commands() == []


def test_service_unit_runs_the_command_from_the_current_venv():
    app = p.App(name="web", source=".", command="python -m web --rate 50%")
    unit = app_module.service_unit(app, f"{BASE}/apps/web")
    assert f"WorkingDirectory={BASE}/apps/web/current\n" in unit
    assert f"ExecStart={BASE}/apps/web/current/.venv/bin/python -m web --rate 50%%\n" in unit
    assert "Restart=always\n" in unit
    assert "Type=exec\n" in unit


def test_service_unit_sets_the_environment():
    app = p.App(name="web", source=".", command="web",
                environment=(("NTFY_TOPIC", "shop"), ("GREETING", 'say "hi" at 100% \\o/')))
    unit = app_module.service_unit(app, f"{BASE}/apps/web")
    assert 'Environment="NTFY_TOPIC=shop"\n' in unit
    assert 'Environment="GREETING=say \\"hi\\" at 100%% \\\\o/"\n' in unit


def test_tarball_skips_the_ignored_names(project):
    with tarfile.open(fileobj=io.BytesIO(app_module._tarball(project))) as tar:
        names = {name.removeprefix("./") for name in tar.getnames()}
    assert {"uv.lock", "pyproject.toml", "web.py"} <= names
    assert not names & {".git", ".git/HEAD", "__pycache__", "web.pyc", "local.db"}


def _workspace(root, sources):
    (root / "pyproject.toml").write_text("[tool.uv.workspace]")
    (root / "uv.lock").write_text("version = 1\n" + "".join(
        f'\n[[package]]\nname = "p{i}"\nsource = {{ {source} }}\n' for i, source in enumerate(sources)))
    for folder in ("libs/a/src", "libs/b", "libs/slicer", "data", "vendor"):
        (root / folder).mkdir(parents=True)
        (root / folder / "file.txt").write_text("x")
    (root / "vendor" / "tool.whl").write_bytes(b"")


def test_tarball_of_a_workspace_takes_only_what_uv_lock_points_to(tmp_path):
    _workspace(tmp_path, ['virtual = "."', 'editable = "libs/a"', 'editable = "./libs/b"',
                          'path = "vendor/tool.whl"', 'registry = "https://pypi.org/simple"'])
    with tarfile.open(fileobj=io.BytesIO(app_module._tarball(tmp_path, "a"))) as tar:
        names = set(tar.getnames())
    assert {"pyproject.toml", "uv.lock", "libs/a/src/file.txt", "libs/b/file.txt", "vendor/tool.whl"} <= names
    assert not any(name.startswith(("data", "libs/slicer", "vendor/file")) for name in names)


def test_tarball_refuses_a_lock_that_points_outside(tmp_path):
    _workspace(tmp_path, ['virtual = "."', 'editable = "../elsewhere"'])
    with pytest.raises(ValueError, match="points outside"):
        app_module._tarball(tmp_path, "a")


def test_tarball_without_package_takes_the_whole_project(tmp_path):
    _workspace(tmp_path, ['virtual = "."'])
    (tmp_path / "main.py").write_text("print('hi')")
    with tarfile.open(fileobj=io.BytesIO(app_module._tarball(tmp_path))) as tar:
        names = {name.removeprefix("./") for name in tar.getnames()}
    assert {"main.py", "pyproject.toml", "uv.lock", "data/file.txt"} <= names


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privileges on Windows")
def test_tarball_follows_a_symlinked_source(project, tmp_path_factory):
    link = tmp_path_factory.mktemp("links") / "web"
    link.symlink_to(project)
    with tarfile.open(fileobj=io.BytesIO(app_module._tarball(link))) as tar:
        names = {name.removeprefix("./") for name in tar.getnames()}
    assert {"uv.lock", "web.py"} <= names


def test_tarball_needs_a_lock_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        app_module._tarball(tmp_path)


def test_deploy_app(fake, project):
    old = ["20200101T000000000000Z", "20200102T000000000000Z", "20200103T000000000000Z"]
    conn = fake({"Linger": "yes", "ls -1": "\n".join(old)})
    app = p.App(name="web", source=str(project), command="web", package="web")

    release = p.deploy_app(PYTHON, app)

    directory = f"{BASE}/apps/web"
    assert release.path.startswith(f"{directory}/releases/")
    commands = conn.commands()
    sync = next(cmd for cmd in commands if " sync " in cmd)
    assert f"--python {PYTHON.path} --package web" in sync
    assert "--frozen --no-dev --no-editable" in sync
    assert (f"chmod 600 {directory}/pyeasydeploy-web.service && "
            f"ln -sfn {release.path} {directory}/current") in commands
    assert any(c.endswith(f"systemctl --user enable {directory}/pyeasydeploy-web.service && "
                          "systemctl --user daemon-reload && "
                          "systemctl --user restart pyeasydeploy-web.service") for c in commands)
    assert sum("echo $HOME" in c for c in commands) == 1
    assert any(c.endswith(f"rm -rf {directory}/releases/{old[0]}") for c in commands)
    assert not any(f"releases/{old[2]}" in c for c in commands)
    assert "ExecStart" in conn.puts()[f"{directory}/pyeasydeploy-web.service"]


def test_deploy_app_needs_linger_before_touching_anything(fake, project):
    conn = fake({"Linger": "no"})
    with pytest.raises(RuntimeError, match="loginctl enable-linger u"):
        p.deploy_app(PYTHON, p.App(name="web", source=str(project), command="web"))
    assert conn.puts() == {}


def test_a_failed_install_removes_its_release(fake, project):
    conn = fake({"Linger": "yes"})
    original = conn.run

    def run(cmd, **kw):
        if " sync " in cmd:
            raise RuntimeError("no network")
        return original(cmd, **kw)

    conn.run = run
    with pytest.raises(RuntimeError, match="no network"):
        p.deploy_app(PYTHON, p.App(name="web", source=str(project), command="web"))
    removed = [cmd for cmd in conn.commands() if "rm -rf " in cmd]
    assert len(removed) == 1 and removed[0].split("rm -rf ")[1].count(f"{BASE}/apps/web/releases/") == 2


def test_app_controls(fake):
    conn = fake()
    p.app_status(SERVER, "web")
    p.app_logs(SERVER, "web", lines=20)
    p.restart_app(SERVER, "web")
    p.stop_app(SERVER, "web")
    commands = conn.commands()
    assert "systemctl --user status --no-pager pyeasydeploy-web.service" in commands[0]
    assert "journalctl --user --no-pager -u pyeasydeploy-web.service -n 20" in commands[1]
    assert commands[2].endswith("systemctl --user restart pyeasydeploy-web.service")
    assert commands[3].endswith("systemctl --user stop pyeasydeploy-web.service")
