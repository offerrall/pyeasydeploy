import io
from pathlib import Path

import pytest

import pyeasydeploy as p
from pyeasydeploy import packages

PY = p.PythonInstance(version="3.11", executable="/usr/bin/python3.11")
VENV = p.Venv(python=PY, path="/home/u/venvs/app")
ENV = "export VIRTUAL_ENV=/home/u/venvs/app && export PATH=/home/u/venvs/app/bin:\"$PATH\" && "


class Result:
    def __init__(self, stdout="", ok=True):
        self.stdout, self.ok = stdout, ok


class FakeConn:
    """Records what would reach the server; answers commands by prefix."""

    def __init__(self, responses=None, sudo_password="pw"):
        self.responses = responses or {}
        self.calls = []
        self.config = type("Config", (), {"sudo": type("Sudo", (), {"password": sudo_password})()})()

    def _answer(self, cmd):
        return next((r for prefix, r in self.responses.items() if cmd.startswith(prefix)), Result())

    def run(self, cmd, **kw):
        self.calls.append(("run", cmd))
        return self._answer(cmd)

    def sudo(self, cmd, **kw):
        self.calls.append(("sudo", cmd))
        return self._answer(cmd)

    def put(self, local, remote):
        content = local.getvalue() if isinstance(local, io.StringIO) else Path(local).name
        self.calls.append(("put", content, remote))


# Models

def test_models_accept_valid_values():
    service = p.SupervisorService(name="web", command="python -m web",
                                  extra=(p.Option(key="priority", value=5),))
    assert service.extra[0].value == 5
    assert p.Host(address="h", user="u", auth=p.Key(path="~/.ssh/k")).port == 22


@pytest.mark.parametrize("build", [
    lambda: p.PythonInstance(version="v3", executable="/usr/bin/python3"),
    lambda: p.PythonInstance(version="3.11", executable="usr/bin/python3"),
    lambda: p.Venv(python=PY, path="venvs/app"),
    lambda: p.Host(address="h", user="u", auth="pw"),
    lambda: p.Host(address="h", user="u", auth=p.Password(value="p"), port=0),
    lambda: p.Host(address="h", user="u", auth=p.Password(value="p"), port=True),
    lambda: p.Host(address="a b", user="u", auth=p.Password(value="p")),
    lambda: p.SupervisorService(name="my app", command="c"),
    lambda: p.SupervisorService(name="a]", command="c"),
    lambda: p.SupervisorService(name="a", command="  "),
    lambda: p.SupervisorService(name="a", command="c", autostart=1),
    lambda: p.SupervisorService(name="a", command="c", directory="srv"),
    lambda: p.SupervisorService(name="a", command="c", extra=[p.Option(key="k", value=1)]),
    lambda: p.SupervisorService(name="a", command="c", extra=(p.Option(key="command", value="x"),)),
    lambda: p.SupervisorService(name="a", command="c",
                                extra=(p.Option(key="k", value=1), p.Option(key="k", value=2))),
    lambda: p.Option(key="a=b", value=1),
    lambda: p.Option(key="k", value="a\nb"),
    lambda: p.Option(key="k", value=1.5),
])
def test_models_reject_invalid_values(build):
    with pytest.raises((TypeError, ValueError)):
        build()


# Connection

def test_connect_with_password_reuses_it_for_sudo():
    conn = p.connect(p.Host(address="h", user="u", auth=p.Password(value="pw"), port=2222))
    assert (conn.host, conn.user, conn.port) == ("h", "u", 2222)
    assert conn.connect_kwargs == {"password": "pw"}
    assert conn.config.sudo.password == "pw"


def test_connect_with_key_needs_its_own_sudo_password():
    conn = p.connect(p.Host(address="h", user="u", auth=p.Key(path="k")))
    assert conn.connect_kwargs == {"key_filename": ["k"]}  # Fabric keeps key files in a list
    assert not p.has_sudo_password(conn)
    conn = p.connect(p.Host(address="h", user="u", auth=p.Key(path="k"), sudo_password="s"))
    assert conn.config.sudo.password == "s"


def test_sudo_functions_refuse_without_a_password():
    conn = FakeConn(sudo_password=None)
    with pytest.raises(PermissionError):
        p.supervisor_restart(conn, "web")
    assert conn.calls == []


# Python

LS = "\n".join(f"/usr/bin/{n}" for n in
               ["python3", "python3.11", "python3.11-config", "python3.9", "python3.1", "python3-qt"])


def test_finds_real_interpreters_newest_first():
    found = p.get_python_instances(FakeConn({"ls -1": Result(LS)}), verbose=False)
    assert [i.version for i in found] == ["3.11", "3.9", "3.1", "3"]


@pytest.mark.parametrize("wanted, version", [("3.1", "3.1"), ("3", "3.11"), ("3.9", "3.9")])
def test_versions_match_by_components(wanted, version):
    conn = FakeConn({"ls -1": Result(LS)})
    assert p.get_target_python_instance(conn, wanted, verbose=False).version == version


def test_missing_versions_fail_clearly():
    with pytest.raises(RuntimeError, match="Available: 3.11, 3.9, 3.1, 3"):
        p.get_target_python_instance(FakeConn({"ls -1": Result(LS)}), "3.12", verbose=False)
    with pytest.raises(RuntimeError, match="No python3 interpreter"):
        p.get_python_instances(FakeConn({"ls -1": Result("", ok=False)}), verbose=False)


# Venvs

def test_create_venv_rebuilds_an_existing_one():
    conn = FakeConn({"test -d": Result(ok=True)})
    venv = p.create_venv(conn, PY, "/home/u/venvs/app", verbose=False)
    assert venv == VENV
    assert conn.calls == [
        ("run", "test -d /home/u/venvs/app"),
        ("run", "rm -rf /home/u/venvs/app"),
        ("run", "/usr/bin/python3.11 -m venv /home/u/venvs/app"),
        ("run", ENV + "python -m pip install -q uv"),
    ]


def test_create_venv_can_reuse_one():
    conn = FakeConn({"test -d": Result(ok=True)})
    p.create_venv(conn, PY, "/home/u/venvs/app", verbose=False, recreate=False)
    assert conn.calls == [("run", "test -d /home/u/venvs/app"),
                          ("run", ENV + "python -m pip install -q uv")]


def test_system_roots_are_never_removed():
    conn = FakeConn()
    for build in (lambda: p.create_venv(conn, PY, "/home/", verbose=False),
                  lambda: p.delete_venv(conn, p.Venv(python=PY, path="/usr"), verbose=False),
                  lambda: p.upload_directory(conn, ".", "/etc/./", verbose=False)):
        with pytest.raises(ValueError, match="system root"):
            build()
    assert conn.calls == []


# Uploads

@pytest.fixture
def project(tmp_path):
    (tmp_path / "pkg" / "__pycache__").mkdir(parents=True)
    (tmp_path / "pkg" / "a.py").write_text("x")
    (tmp_path / "pkg" / "__pycache__" / "a.cpython.pyc").write_text("x")
    (tmp_path / "data.db").write_text("x")
    (tmp_path / "README.md").write_text("x")
    return tmp_path


def test_upload_directory_replaces_the_destination(project):
    conn = FakeConn()
    p.upload_directory(conn, str(project), "/srv/app", verbose=False, mode=0o644)
    assert conn.calls[0] == ("run", "rm -rf /srv/app")
    assert ("run", "mkdir -p /srv/app/pkg /srv/app") in conn.calls
    assert sorted(c[2] for c in conn.calls if c[0] == "put") == ["/srv/app/README.md", "/srv/app/pkg/a.py"]
    assert conn.calls[-1] == ("run", "find /srv/app -type f -exec chmod 644 {} +")


def test_upload_file_with_mode(project):
    conn = FakeConn()
    p.upload_file(conn, str(project / "README.md"), "/srv/app//README.md", verbose=False, mode=0o600)
    assert conn.calls == [
        ("run", "rm -rf /srv/app/README.md"),
        ("run", "mkdir -p /srv/app"),
        ("put", "README.md", "/srv/app/README.md"),
        ("run", "chmod 600 /srv/app/README.md"),
    ]


@pytest.mark.parametrize("mode", [True, -1, 0o10000, "644"])
def test_bad_modes_are_rejected(project, mode):
    with pytest.raises((TypeError, ValueError)):
        p.upload_file(FakeConn(), str(project / "README.md"), "/srv/a", mode=mode)


# Packages

def test_install_packages():
    conn = FakeConn()
    p.install_packages(conn, VENV, ["fastapi", "uvicorn[standard]"], verbose=False)
    assert conn.calls == [("run", ENV + "uv pip install fastapi 'uvicorn[standard]'")]
    conn = FakeConn()
    p.install_packages(conn, VENV, ["x"], use_uv=False, force=True, verbose=False)
    assert conn.calls == [("run", ENV + "python -m pip install --force-reinstall x")]


def test_install_local_package_cleans_up_even_when_it_fails(project):
    conn = FakeConn({"mktemp -d": Result("/tmp/pyeasydeploy.abc\n")})
    conn.run = lambda cmd, _run=conn.run, **kw: (_ for _ in ()).throw(RuntimeError("pip failed")) \
        if "uv pip install" in cmd else _run(cmd, **kw)
    with pytest.raises(RuntimeError):
        p.install_local_package(conn, VENV, str(project / "pkg"), verbose=False)
    assert conn.calls[-1] == ("run", "rm -rf /tmp/pyeasydeploy.abc")


def test_private_repositories_are_cloned_here(monkeypatch, project):
    def clone(cmd, **kw):
        assert cmd[:6] == ["git", "clone", "--depth", "1", "--branch", "v2"]
        (Path(cmd[-1]) / ".git").mkdir(parents=True)
        (Path(cmd[-1]) / "pyproject.toml").write_text("x")
        return type("Done", (), {"returncode": 0})()
    monkeypatch.setattr(packages.subprocess, "run", clone)
    conn = FakeConn({"mktemp -d": Result("/tmp/pyeasydeploy.abc\n")})
    p.install_package_from_private_github(conn, VENV, "git@github.com:o/r.git", branch="v2", verbose=False)
    assert [c[1] for c in conn.calls if c[0] == "put"] == ["pyproject.toml"]
    assert ("run", ENV + "uv pip install /tmp/pyeasydeploy.abc") in conn.calls


# Supervisor

SERVICE = p.SupervisorService(name="web", command="/v/bin/python -m web", directory="/srv",
                              autorestart=False, stdout_logfile=None,
                              extra=(p.Option(key="priority", value=3),
                                     p.Option(key="redirect_stderr", value=True)))


def test_config_text():
    assert p.create_supervisor_config(SERVICE) == (
        "[program:web]\ncommand=/v/bin/python -m web\ndirectory=/srv\nautostart=true\n"
        "autorestart=false\nstderr_logfile=/var/log/supervisor/%(program_name)s_err.log\n"
        "priority=3\nredirect_stderr=true\n"
    )


@pytest.mark.parametrize("os_release, config", [
    ("ID=debian\n", "/etc/supervisor/conf.d/web.conf"),
    ('ID=linuxmint\nID_LIKE="ubuntu debian"\n', "/etc/supervisor/conf.d/web.conf"),
    ("ID=endeavouros\nID_LIKE=arch\n", "/etc/supervisor.d/web.ini"),
])
def test_deploy_uses_the_distribution_layout(os_release, config):
    conn = FakeConn({"cat /etc/os-release": Result(os_release),
                     "mktemp /tmp": Result("/tmp/pyeasydeploy.conf.x\n")})
    p.deploy_supervisor_service(conn, SERVICE, verbose=False)
    assert ("put", p.create_supervisor_config(SERVICE), "/tmp/pyeasydeploy.conf.x") in conn.calls
    assert ("sudo", f"mv /tmp/pyeasydeploy.conf.x {config}") in conn.calls
    assert conn.calls[-3:] == [("sudo", "supervisorctl reread"), ("sudo", "supervisorctl update"),
                               ("run", "rm -f /tmp/pyeasydeploy.conf.x")]


def test_unsupported_distributions_fail():
    with pytest.raises(RuntimeError, match="fedora"):
        p.install_supervisor(FakeConn({"cat /etc/os-release": Result("ID=fedora\n")}))


def test_service_commands():
    conn = FakeConn()
    p.supervisor_start(conn, "my app", verbose=False)
    p.supervisor_status(conn)
    assert conn.calls == [("sudo", "supervisorctl start 'my app'"), ("sudo", "supervisorctl status")]
