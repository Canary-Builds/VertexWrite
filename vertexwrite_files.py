"""Storage URI and backend primitives for VertexWrite.

This module stays free of GTK and SSH dependencies so the editor can migrate
away from direct ``Path`` calls before remote files are introduced.
"""
from __future__ import annotations

import getpass
import os
import posixpath
import shlex
import socket
import stat
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import quote, unquote, urlsplit, urlunsplit

LOCAL_SCHEMES = {"file", "local"}
SUPPORTED_SCHEMES = LOCAL_SCHEMES | {"sftp"}
SFTP_HOME_PATHS = {"/.", "/~"}
FileKind = Literal["file", "directory", "symlink", "other"]


class StorageError(Exception):
    """Base storage-layer exception."""


class UnsupportedBackendError(StorageError):
    """Raised when no backend is registered for a URI scheme."""


class ParamikoUnavailableError(StorageError):
    """Raised when SFTP is requested without Paramiko installed."""


@dataclass(frozen=True, slots=True)
class FileUri:
    """Stable document identifier for local and future remote files."""

    scheme: str
    path: str
    authority: str = ""

    def __post_init__(self):
        scheme = self.scheme.lower()
        if scheme == "local":
            scheme = "file"
        if scheme not in SUPPORTED_SCHEMES:
            raise ValueError(f"unsupported file URI scheme: {self.scheme}")
        if not self.path:
            raise ValueError("file URI path cannot be empty")
        if scheme == "file":
            object.__setattr__(self, "authority", "")
            if not self.path.startswith("/"):
                raise ValueError("file URI paths must be absolute")
        elif scheme == "sftp":
            if not self.path.startswith("/"):
                raise ValueError("sftp URI paths must be absolute")
            _validate_sftp_authority(self.authority)
        object.__setattr__(self, "scheme", scheme)

    @classmethod
    def parse(cls, value: str | os.PathLike[str] | FileUri) -> FileUri:
        if isinstance(value, FileUri):
            return value
        text = os.fspath(value)
        if not text:
            raise ValueError("file URI cannot be empty")
        parts = urlsplit(text)
        if not parts.scheme:
            return cls.from_path(Path(text).expanduser())

        scheme = parts.scheme.lower()
        if scheme == "local":
            scheme = "file"
        if scheme not in SUPPORTED_SCHEMES:
            raise ValueError(f"unsupported file URI scheme: {parts.scheme}")

        if scheme == "file":
            if parts.netloc and parts.netloc != "localhost":
                raise ValueError("file URI must not contain a remote authority")
            path = unquote(parts.path)
            return cls("file", path, "")

        return cls("sftp", unquote(parts.path or "/"), parts.netloc)

    @classmethod
    def from_path(cls, path: Path | str | os.PathLike[str]) -> FileUri:
        resolved = Path(path).expanduser().resolve()
        return cls.parse(resolved.as_uri())

    @property
    def is_local(self) -> bool:
        return self.scheme == "file"

    @property
    def is_remote(self) -> bool:
        return not self.is_local

    @property
    def name(self) -> str:
        clean = self.path.rstrip("/")
        return posixpath.basename(clean) or self.path

    @property
    def parent(self) -> FileUri:
        clean = self.path.rstrip("/")
        parent = posixpath.dirname(clean) or "/"
        return FileUri(self.scheme, parent, self.authority)

    def to_path(self) -> Path:
        if not self.is_local:
            raise ValueError(f"{self.scheme} URI cannot be converted to Path")
        return Path(self.path)

    def with_path(self, path: str) -> FileUri:
        return FileUri(self.scheme, path, self.authority)

    def display(self) -> str:
        if self.is_local:
            return str(self.to_path())
        return f"{self.scheme}://{self.authority}{self.path}"

    def __str__(self) -> str:
        encoded_path = quote(self.path, safe="/~!$&'()*+,;=:@")
        return urlunsplit((self.scheme, self.authority, encoded_path, "", ""))


@dataclass(frozen=True, slots=True)
class FileInfo:
    uri: FileUri
    kind: FileKind
    size: int
    modified_ns: int
    permissions: int | None = None

    @property
    def name(self) -> str:
        return self.uri.name

    @property
    def is_file(self) -> bool:
        return self.kind == "file"

    @property
    def is_dir(self) -> bool:
        return self.kind == "directory"


@dataclass(frozen=True, slots=True)
class SftpConnectionInfo:
    host: str
    port: int
    username: str | None
    path: str
    authority: str

    @property
    def label(self) -> str:
        user = f"{self.username}@" if self.username else ""
        return f"{user}{self.host}:{self.port}"


class FileBackend(Protocol):
    schemes: tuple[str, ...]

    def stat(self, uri: FileUri | str | os.PathLike[str]) -> FileInfo:
        ...

    def list_dir(self, uri: FileUri | str | os.PathLike[str]) -> list[FileInfo]:
        ...

    def read_bytes(self, uri: FileUri | str | os.PathLike[str]) -> bytes:
        ...

    def write_bytes_atomic(
            self,
            uri: FileUri | str | os.PathLike[str],
            data: bytes) -> FileInfo:
        ...


class LocalBackend:
    """Backend for local filesystem access."""

    schemes = ("file", "local")

    def stat(self, uri: FileUri | str | os.PathLike[str]) -> FileInfo:
        file_uri = self._local_uri(uri)
        path = file_uri.to_path()
        st = path.lstat()
        return FileInfo(
            uri=file_uri,
            kind=_stat_kind(st.st_mode),
            size=st.st_size,
            modified_ns=st.st_mtime_ns,
            permissions=stat.S_IMODE(st.st_mode),
        )

    def list_dir(self, uri: FileUri | str | os.PathLike[str]) -> list[FileInfo]:
        path = self._local_uri(uri).to_path()
        infos = [self.stat(entry) for entry in path.iterdir()]
        return sorted(infos, key=lambda info: (not info.is_dir, info.name.lower()))

    def read_bytes(self, uri: FileUri | str | os.PathLike[str]) -> bytes:
        return self._local_uri(uri).to_path().read_bytes()

    def write_bytes_atomic(
            self,
            uri: FileUri | str | os.PathLike[str],
            data: bytes) -> FileInfo:
        target = self._local_uri(uri).to_path()
        tmp_path = None
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=str(target.parent),
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if target.exists():
                os.chmod(tmp_path, stat.S_IMODE(target.stat().st_mode))
            os.replace(tmp_path, target)
            _fsync_dir(target.parent)
        except Exception:
            if tmp_path is not None:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise
        return self.stat(target)

    def mkdir(self, uri: FileUri | str | os.PathLike[str]) -> FileInfo:
        path = self._local_uri(uri).to_path()
        path.mkdir(parents=True, exist_ok=True)
        return self.stat(path)

    def rename(
            self,
            source: FileUri | str | os.PathLike[str],
            target: FileUri | str | os.PathLike[str]) -> FileInfo:
        source_path = self._local_uri(source).to_path()
        target_path = self._local_uri(target).to_path()
        os.replace(source_path, target_path)
        _fsync_dir(target_path.parent)
        return self.stat(target_path)

    def delete(self, uri: FileUri | str | os.PathLike[str]) -> None:
        path = self._local_uri(uri).to_path()
        if path.is_dir() and not path.is_symlink():
            path.rmdir()
        else:
            path.unlink()
        _fsync_dir(path.parent)

    def _local_uri(self, uri: FileUri | str | os.PathLike[str]) -> FileUri:
        file_uri = FileUri.parse(uri)
        if not file_uri.is_local:
            raise UnsupportedBackendError(
                f"LocalBackend cannot handle {file_uri.scheme} URIs"
            )
        return file_uri


class SftpBackend:
    """Strict SFTP backend using SSH agent/key auth and known_hosts checks."""

    schemes = ("sftp",)

    def __init__(
            self,
            *,
            known_hosts: Path | str | None = None,
            ssh_config: Path | str | None = None,
            connect_timeout: float = 15.0,
            client_factory: Any | None = None):
        self.known_hosts = Path(known_hosts).expanduser() if known_hosts else None
        self.ssh_config = Path(ssh_config).expanduser() if ssh_config else None
        self.connect_timeout = connect_timeout
        self._client_factory = client_factory

    def connection_info(
            self,
            uri: FileUri | str | os.PathLike[str]) -> SftpConnectionInfo:
        file_uri = self._sftp_uri(uri)
        parsed = urlsplit(f"sftp://{file_uri.authority}/")
        port = parsed.port or 22
        username = unquote(parsed.username) if parsed.username else None
        assert parsed.hostname is not None
        return SftpConnectionInfo(
            host=parsed.hostname,
            port=port,
            username=username,
            path=file_uri.path,
            authority=file_uri.authority,
        )

    def stat(self, uri: FileUri | str | os.PathLike[str]) -> FileInfo:
        file_uri = self._sftp_uri(uri)
        with self._session(file_uri) as (sftp, _info):
            file_uri = self._resolve_runtime_uri(sftp, file_uri)
            return self._info_from_attrs(file_uri, sftp.lstat(file_uri.path))

    def list_dir(self, uri: FileUri | str | os.PathLike[str]) -> list[FileInfo]:
        file_uri = self._sftp_uri(uri)
        with self._session(file_uri) as (sftp, _info):
            file_uri = self._resolve_runtime_uri(sftp, file_uri)
            infos = []
            for attrs in sftp.listdir_attr(file_uri.path):
                child_path = posixpath.join(file_uri.path, attrs.filename)
                child_uri = file_uri.with_path(child_path)
                infos.append(self._info_from_attrs(child_uri, attrs))
        return sorted(infos, key=lambda info: (not info.is_dir, info.name.lower()))

    def read_bytes(self, uri: FileUri | str | os.PathLike[str]) -> bytes:
        file_uri = self._sftp_uri(uri)
        with self._session(file_uri) as (sftp, _info):
            file_uri = self._resolve_runtime_uri(sftp, file_uri)
            with sftp.open(file_uri.path, "rb") as handle:
                return handle.read()

    def write_bytes_atomic(
            self,
            uri: FileUri | str | os.PathLike[str],
        data: bytes) -> FileInfo:
        file_uri = self._sftp_uri(uri)
        with self._session(file_uri) as (sftp, _info):
            file_uri = self._resolve_runtime_uri(sftp, file_uri)
            directory = posixpath.dirname(file_uri.path) or "/"
            name = posixpath.basename(file_uri.path.rstrip("/"))
            tmp_path = posixpath.join(
                directory,
                f".{name}.{uuid.uuid4().hex}.tmp",
            )
            try:
                with sftp.open(tmp_path, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                self._copy_mode_if_present(sftp, file_uri.path, tmp_path)
                self._posix_rename(sftp, tmp_path, file_uri.path)
            except Exception:
                try:
                    sftp.remove(tmp_path)
                except OSError:
                    pass
                raise
            return self._info_from_attrs(file_uri, sftp.lstat(file_uri.path))

    def mkdir(self, uri: FileUri | str | os.PathLike[str]) -> FileInfo:
        file_uri = self._sftp_uri(uri)
        with self._session(file_uri) as (sftp, _info):
            file_uri = self._resolve_runtime_uri(sftp, file_uri)
            sftp.mkdir(file_uri.path)
            return self._info_from_attrs(file_uri, sftp.lstat(file_uri.path))

    def rename(
            self,
            source: FileUri | str | os.PathLike[str],
            target: FileUri | str | os.PathLike[str]) -> FileInfo:
        source_uri = self._sftp_uri(source)
        target_uri = self._sftp_uri(target)
        if source_uri.authority != target_uri.authority:
            raise StorageError("cannot rename across SFTP hosts")
        with self._session(source_uri) as (sftp, _info):
            source_uri = self._resolve_runtime_uri(sftp, source_uri)
            target_uri = self._resolve_runtime_uri(sftp, target_uri)
            self._posix_rename(sftp, source_uri.path, target_uri.path)
            return self._info_from_attrs(target_uri, sftp.lstat(target_uri.path))

    def delete(self, uri: FileUri | str | os.PathLike[str]) -> None:
        file_uri = self._sftp_uri(uri)
        with self._session(file_uri) as (sftp, _info):
            file_uri = self._resolve_runtime_uri(sftp, file_uri)
            attrs = sftp.lstat(file_uri.path)
            mode = getattr(attrs, "st_mode", None)
            if mode is not None and stat.S_ISDIR(mode):
                sftp.rmdir(file_uri.path)
            else:
                sftp.remove(file_uri.path)

    def _sftp_uri(self, uri: FileUri | str | os.PathLike[str]) -> FileUri:
        file_uri = FileUri.parse(uri)
        if file_uri.scheme != "sftp":
            raise UnsupportedBackendError(
                f"SftpBackend cannot handle {file_uri.scheme} URIs"
            )
        return file_uri

    def normalize_uri(self, uri: FileUri | str | os.PathLike[str]) -> FileUri:
        file_uri = self._sftp_uri(uri)
        with self._session(file_uri) as (sftp, _info):
            return self._resolve_runtime_uri(sftp, file_uri)

    @contextmanager
    def _session(self, uri: FileUri):
        client = self._make_client()
        info = self.connection_info(uri)
        lookup = self._ssh_config_lookup(info.host)
        sftp = None
        try:
            self._prepare_client(client, info, lookup)
            client.connect(**self._connect_kwargs(info, lookup))
            sftp = client.open_sftp()
            yield sftp, info
        finally:
            if sftp is not None:
                sftp.close()
            client.close()

    def _make_client(self):
        if self._client_factory is not None:
            return self._client_factory()
        paramiko = _load_paramiko()
        return paramiko.SSHClient()

    def _prepare_client(
            self,
            client,
            info: SftpConnectionInfo,
            lookup: dict[str, Any]) -> None:
        if self._client_factory is not None:
            if hasattr(client, "load_system_host_keys"):
                client.load_system_host_keys()
            if self.known_hosts and hasattr(client, "load_host_keys"):
                client.load_host_keys(str(self.known_hosts))
            return
        client.load_system_host_keys()
        if self.known_hosts:
            client.load_host_keys(str(self.known_hosts))
        connect_host = lookup.get("hostname", info.host)
        port = int(lookup.get("port", info.port))
        host_key_name = lookup.get("hostkeyalias", info.host)
        aliases = _host_key_candidates(info.host, connect_host, host_key_name, port)
        client.set_missing_host_key_policy(_KnownHostsAliasPolicy(aliases))

    def _connect_kwargs(
            self,
            info: SftpConnectionInfo,
            lookup: dict[str, Any] | None = None) -> dict[str, Any]:
        lookup = lookup or self._ssh_config_lookup(info.host)
        connect_host = lookup.get("hostname", info.host)
        host_key_name = lookup.get("hostkeyalias", info.host)
        port = int(lookup.get("port", info.port))
        username = info.username or lookup.get("user") or getpass.getuser()
        kwargs: dict[str, Any] = {
            "hostname": host_key_name,
            "port": port,
            "username": username,
            "allow_agent": True,
            "look_for_keys": True,
            "timeout": self.connect_timeout,
            "banner_timeout": self.connect_timeout,
            "auth_timeout": self.connect_timeout,
        }
        identity_files = lookup.get("identityfile")
        if identity_files:
            kwargs["key_filename"] = identity_files
        proxy_command = lookup.get("proxycommand")
        if proxy_command:
            kwargs["sock"] = _load_paramiko().ProxyCommand(proxy_command)
        elif connect_host != host_key_name:
            kwargs["sock"] = self._open_direct_sock(connect_host, port)
        return kwargs

    def _open_direct_sock(self, hostname: str, port: int):
        return socket.create_connection((hostname, port), self.connect_timeout)

    def _ssh_config_lookup(self, host: str) -> dict[str, Any]:
        if self._client_factory is not None and self.ssh_config is None:
            return {}
        path = self.ssh_config or Path.home() / ".ssh" / "config"
        if not path.exists():
            return {}
        paramiko = _load_paramiko()
        config = paramiko.SSHConfig()
        with path.open(encoding="utf-8") as handle:
            config.parse(handle)
        return config.lookup(host)

    def _copy_mode_if_present(self, sftp, source: str, target: str) -> None:
        try:
            attrs = sftp.stat(source)
        except OSError:
            return
        mode = getattr(attrs, "st_mode", None)
        if mode is not None:
            sftp.chmod(target, stat.S_IMODE(mode))

    def _resolve_runtime_uri(self, sftp, uri: FileUri) -> FileUri:
        path = self._expand_remote_path(sftp, uri.path)
        if path == uri.path:
            return uri
        return uri.with_path(path)

    def _expand_remote_path(self, sftp, path: str) -> str:
        if path in SFTP_HOME_PATHS:
            return sftp.normalize(".")
        if path.startswith("/~/"):
            return posixpath.join(sftp.normalize("."), path[3:])
        if path.startswith("/./"):
            return posixpath.join(sftp.normalize("."), path[3:])
        return path

    def _posix_rename(self, sftp, source: str, target: str) -> None:
        try:
            sftp.posix_rename(source, target)
        except (AttributeError, OSError) as exc:
            raise StorageError(
                "SFTP server does not support atomic posix rename"
            ) from exc

    def _info_from_attrs(self, uri: FileUri, attrs) -> FileInfo:
        mode = getattr(attrs, "st_mode", None)
        modified = getattr(attrs, "st_mtime", 0) or 0
        return FileInfo(
            uri=uri,
            kind=_stat_kind(mode) if mode is not None else "other",
            size=getattr(attrs, "st_size", 0) or 0,
            modified_ns=int(modified * 1_000_000_000),
            permissions=stat.S_IMODE(mode) if mode is not None else None,
        )


class BackendRegistry:
    """Maps URI schemes to storage backends."""

    def __init__(self, backends: list[FileBackend] | None = None):
        self._backends: dict[str, FileBackend] = {}
        for backend in backends or []:
            self.register(backend)

    def register(self, backend: FileBackend) -> None:
        for scheme in backend.schemes:
            self._backends[scheme] = backend

    def backend_for(self, uri: FileUri | str | os.PathLike[str]) -> FileBackend:
        file_uri = FileUri.parse(uri)
        try:
            return self._backends[file_uri.scheme]
        except KeyError as exc:
            raise UnsupportedBackendError(
                f"no backend registered for {file_uri.scheme} URIs"
            ) from exc


DEFAULT_REGISTRY = BackendRegistry([LocalBackend(), SftpBackend()])


def backend_for(uri: FileUri | str | os.PathLike[str]) -> FileBackend:
    return DEFAULT_REGISTRY.backend_for(uri)


class _KnownHostsAliasPolicy:
    def __init__(self, candidates: list[str]):
        self.candidates = candidates

    def missing_host_key(self, client, hostname: str, key) -> None:
        for candidate in [hostname, *self.candidates]:
            for host_keys in (client._host_keys, client._system_host_keys):  # noqa: SLF001
                known = host_keys.lookup(candidate)
                if known and known.get(key.get_name()) == key:
                    client._host_keys.add(hostname, key.get_name(), key)  # noqa: SLF001
                    return
        raise _load_paramiko().SSHException(
            f"Server {hostname!r} not found in known_hosts"
        )


def _host_key_candidates(
        requested_host: str,
        connect_host: str,
        host_key_name: str,
        port: int) -> list[str]:
    out: list[str] = []
    for host in (host_key_name, requested_host, connect_host):
        if not host:
            continue
        out.append(host)
        out.append(f"[{host}]:{port}")
    unique = []
    seen = set()
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def parse_remote_target(value: str) -> FileUri:
    text = value.strip()
    if not text:
        raise ValueError("remote target cannot be empty")
    if text.startswith("sftp://"):
        uri = FileUri.parse(text)
        if uri.scheme != "sftp":
            raise ValueError("remote target must use SFTP")
        return uri

    tokens = shlex.split(text)
    if tokens and tokens[0] == "ssh":
        tokens = tokens[1:]
    port: str | None = None
    username: str | None = None
    target: str | None = None
    path = ""
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "-p":
            i += 1
            if i >= len(tokens):
                raise ValueError("ssh -p requires a port")
            port = tokens[i]
        elif token.startswith("-p") and len(token) > 2:
            port = token[2:]
        elif token == "-l":
            i += 1
            if i >= len(tokens):
                raise ValueError("ssh -l requires a username")
            username = tokens[i]
        elif token.startswith("-"):
            raise ValueError(f"unsupported ssh option: {token}")
        elif target is None:
            target = token
        elif not path:
            path = token
        else:
            raise ValueError("remote target has too many arguments")
        i += 1

    if target is None:
        raise ValueError("remote target requires a host")
    target, inline_path, inline_port = _split_ssh_target(target)
    if inline_path and not path:
        path = inline_path
    if inline_port and port is None:
        port = inline_port
    if username and "@" not in target:
        target = f"{username}@{target}"
    authority = target
    if port:
        authority = f"{authority}:{port}"
    return FileUri("sftp", _normalize_remote_input_path(path), authority)


def _split_ssh_target(target: str) -> tuple[str, str, str | None]:
    if target.count(":") != 1:
        return target, "", None
    host, tail = target.rsplit(":", 1)
    if not host or not tail:
        return target, "", None
    if tail.isdigit():
        return host, "", tail
    return host, tail, None


def _normalize_remote_input_path(path: str) -> str:
    if not path:
        return "/."
    if path in (".", "~"):
        return f"/{path}"
    if path.startswith("~/"):
        return "/~/" + path[2:]
    if path.startswith("./"):
        return "/./" + path[2:]
    if not path.startswith("/"):
        return "/" + path
    return path


def _reject_password_userinfo(authority: str) -> None:
    if "@" not in authority:
        return
    userinfo = authority.rsplit("@", 1)[0]
    if ":" in userinfo or ":" in unquote(userinfo):
        raise ValueError("URI passwords are not supported")


def _validate_sftp_authority(authority: str) -> None:
    if not authority:
        raise ValueError("sftp URI requires a host")
    _reject_password_userinfo(authority)
    try:
        parsed = urlsplit(f"sftp://{authority}/")
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("sftp URI authority is invalid") from exc
    if not parsed.hostname:
        raise ValueError("sftp URI requires a host")


def _load_paramiko():
    try:
        import paramiko
    except ImportError as exc:
        raise ParamikoUnavailableError(
            "SFTP support requires the 'paramiko' Python package"
        ) from exc
    return paramiko


def _stat_kind(mode: int) -> FileKind:
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "file"
    return "other"


def _fsync_dir(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
