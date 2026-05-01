from pathlib import Path
import stat
import sys

import pytest
import paramiko


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vertexwrite_files import (  # noqa: E402
    BackendRegistry,
    FileUri,
    LocalBackend,
    SftpBackend,
    UnsupportedBackendError,
    _KnownHostsAliasPolicy,
    backend_for,
    parse_remote_target,
)


class _Attrs:
    def __init__(
            self,
            filename: str,
            mode: int,
            size: int = 0,
            mtime: int = 1):
        self.filename = filename
        self.st_mode = mode
        self.st_size = size
        self.st_mtime = mtime


class _RemoteFile:
    def __init__(self, sftp, path: str, mode: str):
        self.sftp = sftp
        self.path = path
        self.mode = mode
        self.data = bytearray()

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        if "w" in self.mode:
            self.sftp.files[self.path] = bytes(self.data)
            self.sftp.modes[self.path] = stat.S_IFREG | 0o600

    def read(self) -> bytes:
        return self.sftp.files[self.path]

    def write(self, data: bytes) -> None:
        self.data.extend(data)

    def flush(self) -> None:
        return


class _FakeSftp:
    def __init__(self):
        self.files = {"/home/marek/readme.md": b"# Old\n"}
        self.modes = {
            "/home/marek": stat.S_IFDIR | 0o755,
            "/home/marek/readme.md": stat.S_IFREG | 0o644,
        }
        self.closed = False

    def lstat(self, path: str):
        if path in self.modes:
            size = len(self.files.get(path, b""))
            return _Attrs(Path(path).name, self.modes[path], size)
        raise FileNotFoundError(path)

    def stat(self, path: str):
        return self.lstat(path)

    def listdir_attr(self, path: str):
        prefix = path.rstrip("/") + "/"
        out = []
        for item_path in sorted(self.modes):
            if item_path == path or not item_path.startswith(prefix):
                continue
            rest = item_path[len(prefix):]
            if "/" not in rest:
                attr = self.lstat(item_path)
                attr.filename = rest
                out.append(attr)
        return out

    def open(self, path: str, mode: str):
        return _RemoteFile(self, path, mode)

    def chmod(self, path: str, mode: int):
        self.modes[path] = stat.S_IFREG | mode

    def mkdir(self, path: str):
        self.modes[path] = stat.S_IFDIR | 0o755

    def remove(self, path: str):
        self.files.pop(path, None)
        self.modes.pop(path, None)

    def rmdir(self, path: str):
        self.modes.pop(path, None)

    def posix_rename(self, source: str, target: str):
        if source in self.files:
            self.files[target] = self.files.pop(source)
        self.modes[target] = self.modes.pop(source)

    def normalize(self, path: str):
        if path == ".":
            return "/home/marek"
        return path

    def close(self):
        self.closed = True


class _FakeClient:
    def __init__(self, sftp: _FakeSftp):
        self.sftp = sftp
        self.connect_kwargs = None
        self.closed = False
        self.loaded_system_keys = False

    def load_system_host_keys(self):
        self.loaded_system_keys = True

    def connect(self, **kwargs):
        self.connect_kwargs = kwargs

    def open_sftp(self):
        return self.sftp

    def close(self):
        self.closed = True


class _AliasBackend(SftpBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sock_target = None

    def _open_direct_sock(self, hostname: str, port: int):
        self.sock_target = (hostname, port)
        return "direct-socket"


def test_file_uri_round_trips_local_paths_with_spaces(tmp_path: Path):
    note = tmp_path / "notes folder" / "my note.md"
    note.parent.mkdir()
    note.write_text("# Note\n", encoding="utf-8")

    uri = FileUri.from_path(note)

    assert str(uri).startswith("file://")
    assert "%20" in str(uri)
    assert uri.name == "my note.md"
    assert uri.parent.to_path() == note.parent.resolve()
    assert uri.to_path() == note.resolve()


def test_plain_path_parses_as_local_file_uri(tmp_path: Path):
    note = tmp_path / "plain.md"
    uri = FileUri.parse(note)

    assert uri.is_local
    assert uri.to_path() == note.resolve()


def test_plain_path_preserves_leading_and_trailing_spaces(tmp_path: Path):
    note = tmp_path / " spaced folder " / " note .md "
    note.parent.mkdir()

    uri = FileUri.parse(note)

    assert uri.to_path() == note.resolve()
    assert uri.name == " note .md "


def test_sftp_uri_parses_without_activating_backend():
    uri = FileUri.parse("sftp://marek@example.com:2222/home/marek/My%20Doc.md")

    assert uri.scheme == "sftp"
    assert uri.authority == "marek@example.com:2222"
    assert uri.path == "/home/marek/My Doc.md"
    assert uri.name == "My Doc.md"
    assert str(uri) == "sftp://marek@example.com:2222/home/marek/My%20Doc.md"


def test_sftp_uri_rejects_password_userinfo():
    with pytest.raises(ValueError, match="password"):
        FileUri.parse("sftp://marek:secret@example.com/home/marek/doc.md")

    with pytest.raises(ValueError, match="password"):
        FileUri.parse("sftp://marek%3Asecret@example.com/home/marek/doc.md")

    with pytest.raises(ValueError, match="host"):
        FileUri.parse("sftp://marek@/home/marek/doc.md")

    with pytest.raises(ValueError, match="authority"):
        FileUri.parse("sftp://marek@example.com:notaport/home/marek/doc.md")


def test_local_backend_stat_list_and_atomic_write(tmp_path: Path):
    backend = LocalBackend()
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "folder").mkdir()
    target = root / "note.md"

    info = backend.write_bytes_atomic(FileUri.from_path(target), b"# Updated\n")

    assert info.is_file
    assert target.read_text(encoding="utf-8") == "# Updated\n"
    assert backend.read_bytes(target) == b"# Updated\n"
    listing = backend.list_dir(root)
    assert [item.name for item in listing] == ["folder", "note.md"]
    assert [item.kind for item in listing] == ["directory", "file"]
    assert backend.stat(root).is_dir


def test_default_registry_handles_local_only(tmp_path: Path):
    note = tmp_path / "note.md"

    assert backend_for(note).schemes == ("file", "local")
    assert backend_for("sftp://example.com/home/marek/note.md").schemes == ("sftp",)


def test_registry_reports_unsupported_remote_backend():
    registry = BackendRegistry([LocalBackend()])

    with pytest.raises(UnsupportedBackendError):
        registry.backend_for("sftp://example.com/home/marek/note.md")


def test_sftp_backend_parses_connection_info():
    backend = SftpBackend()

    info = backend.connection_info(
        "sftp://marek@example.com:2222/home/marek/readme.md"
    )

    assert info.host == "example.com"
    assert info.port == 2222
    assert info.username == "marek"
    assert info.path == "/home/marek/readme.md"
    assert info.label == "marek@example.com:2222"


def test_parse_remote_target_accepts_ssh_alias_shorthand():
    assert str(parse_remote_target("ssh catherine")) == "sftp://catherine/."
    assert str(parse_remote_target("catherine")) == "sftp://catherine/."
    assert (
        str(parse_remote_target("ssh -p 2200 -l marek catherine ~/docs"))
        == "sftp://marek@catherine:2200/~/docs"
    )
    assert (
        str(parse_remote_target("catherine:/srv/docs"))
        == "sftp://catherine/srv/docs"
    )


def test_sftp_backend_uses_strict_agent_key_connection_and_atomic_rename():
    sftp = _FakeSftp()
    clients = []

    def client_factory():
        client = _FakeClient(sftp)
        clients.append(client)
        return client

    backend = SftpBackend(client_factory=client_factory, connect_timeout=3)
    uri = FileUri.parse("sftp://marek@example.com:2222/home/marek/readme.md")

    assert backend.read_bytes(uri) == b"# Old\n"
    listing = backend.list_dir(uri.parent)
    assert [item.name for item in listing] == ["readme.md"]

    info = backend.write_bytes_atomic(uri, b"# New\n")

    assert info.is_file
    assert sftp.files["/home/marek/readme.md"] == b"# New\n"
    assert clients[-1].loaded_system_keys
    assert clients[-1].connect_kwargs == {
        "hostname": "example.com",
        "port": 2222,
        "username": "marek",
        "allow_agent": True,
        "look_for_keys": True,
        "timeout": 3,
        "banner_timeout": 3,
        "auth_timeout": 3,
    }


def test_sftp_backend_normalizes_home_shorthand():
    sftp = _FakeSftp()
    clients = []

    def client_factory():
        client = _FakeClient(sftp)
        clients.append(client)
        return client

    backend = SftpBackend(client_factory=client_factory, connect_timeout=3)

    uri = backend.normalize_uri(parse_remote_target("ssh catherine"))

    assert str(uri) == "sftp://catherine/home/marek"


def test_sftp_backend_uses_ssh_config_alias_for_host_key_name(tmp_path: Path):
    ssh_config = tmp_path / "config"
    key_path = tmp_path / "id_ed25519"
    ssh_config.write_text(
        "\n".join(
            [
                "Host catherine",
                "    HostName 46.250.242.158",
                "    User marek",
                "    Port 64655",
                f"    IdentityFile {key_path}",
            ]
        ),
        encoding="utf-8",
    )
    backend = _AliasBackend(ssh_config=ssh_config, connect_timeout=3)
    info = backend.connection_info(parse_remote_target("ssh catherine"))

    kwargs = backend._connect_kwargs(info)

    assert kwargs["hostname"] == "catherine"
    assert kwargs["port"] == 64655
    assert kwargs["username"] == "marek"
    assert kwargs["key_filename"] == [str(key_path)]
    assert kwargs["sock"] == "direct-socket"
    assert backend.sock_target == ("46.250.242.158", 64655)


def test_known_hosts_alias_policy_checks_system_host_keys():
    class Client:
        def __init__(self):
            self._host_keys = paramiko.HostKeys()
            self._system_host_keys = paramiko.HostKeys()

    client = Client()
    key = paramiko.RSAKey.generate(1024)
    client._system_host_keys.add("46.250.242.158", key.get_name(), key)
    policy = _KnownHostsAliasPolicy(["46.250.242.158"])

    policy.missing_host_key(client, "[catherine]:64655", key)

    known = client._host_keys.lookup("[catherine]:64655")
    assert known is not None
    assert known[key.get_name()] == key
