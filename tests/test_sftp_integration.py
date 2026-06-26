"""Real-socket SFTP integration tests.

These spin up an actual paramiko SSH+SFTP server on localhost and drive it
through ``SftpBackend``, so they exercise the genuine transport, channel and
SFTP protocol rather than mocks. They validate two things the unit tests
cannot:

* a streaming upload/download round-trip works end to end, and
* a server that accepts the connection but never answers an SFTP request makes
  the transfer raise (via the per-operation timeout) instead of hanging
  forever — the bug these tests exist to pin down.

The server scaffolding is environment-sensitive (threads, sockets, auth). If it
cannot be brought up, the tests skip rather than fail.
"""
from __future__ import annotations

import os
import socket
import stat
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

paramiko = pytest.importorskip("paramiko")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vertexwrite_files import SftpBackend, TransferCancelled  # noqa: E402


class _Server(paramiko.ServerInterface):
    """Accepts any auth and a single SFTP session."""

    def check_auth_none(self, username):
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return "none,password,publickey"

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


class _Handle(paramiko.SFTPHandle):
    def stat(self):
        try:
            return paramiko.SFTPAttributes.from_stat(
                os.fstat(self.readfile.fileno()))
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)


class _FSSFTP(paramiko.SFTPServerInterface):
    """Minimal filesystem-backed SFTP server rooted at ``ROOT``."""

    ROOT = "/"

    def _real(self, path: str) -> str:
        return os.path.normpath(os.path.join(self.ROOT, path.lstrip("/")))

    def list_folder(self, path):
        real = self._real(path)
        try:
            out = []
            for name in os.listdir(real):
                attr = paramiko.SFTPAttributes.from_stat(
                    os.lstat(os.path.join(real, name)))
                attr.filename = name
                out.append(attr)
            return out
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def stat(self, path):
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(self._real(path)))
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def lstat(self, path):
        try:
            return paramiko.SFTPAttributes.from_stat(os.lstat(self._real(path)))
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def open(self, path, flags, attr):
        real = self._real(path)
        try:
            fd = os.open(real, flags, getattr(attr, "st_mode", None) or 0o644)
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)
        if flags & os.O_WRONLY:
            mode = "ab" if flags & os.O_APPEND else "wb"
        elif flags & os.O_RDWR:
            mode = "a+b" if flags & os.O_APPEND else "r+b"
        else:
            mode = "rb"
        try:
            fileobj = os.fdopen(fd, mode)
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)
        handle = _Handle(flags)
        handle.filename = real
        handle.readfile = fileobj
        handle.writefile = fileobj
        return handle

    def mkdir(self, path, attr):
        try:
            os.mkdir(self._real(path))
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)
        return paramiko.SFTP_OK

    def chattr(self, path, attr):
        try:
            if getattr(attr, "st_mode", None) is not None:
                os.chmod(self._real(path), attr.st_mode & 0o7777)
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)
        return paramiko.SFTP_OK


class _StallSFTP(paramiko.SFTPServerInterface):
    """Accepts the SFTP subsystem but never answers a request."""

    def _stall(self, *args, **kwargs):
        time.sleep(60)
        return paramiko.SFTP_FAILURE

    list_folder = _stall
    stat = _stall
    lstat = _stall
    open = _stall


@contextmanager
def _sftp_server(sftp_class, root: str):
    host_key = paramiko.RSAKey.generate(2048)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    transports = []

    def serve():
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        server_class = type(
            "BoundSFTP", (sftp_class,), {"ROOT": root})
        transport = paramiko.Transport(conn)
        transports.append(transport)
        transport.add_server_key(host_key)
        transport.set_subsystem_handler(
            "sftp", paramiko.SFTPServer, server_class)
        try:
            transport.start_server(server=_Server())
        except Exception:  # noqa: BLE001 - client may drop during stall tests
            pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        listener.close()
        for transport in transports:
            try:
                transport.close()
            except Exception:  # noqa: BLE001
                pass


def _backend(**kwargs) -> SftpBackend:
    def factory():
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    return SftpBackend(client_factory=factory, **kwargs)


def _uri(port: int, path: str) -> str:
    return f"sftp://127.0.0.1:{port}{path}"


def test_real_round_trip_upload_then_download(tmp_path: Path):
    """Upload a folder to a real SFTP server, then download it back."""
    remote_root = tmp_path / "remote"
    remote_root.mkdir()
    src = tmp_path / "proj"
    (src / "sub").mkdir(parents=True)
    (src / "a.md").write_bytes(b"# A\n")
    (src / "sub" / "b.md").write_bytes(b"bee\n")

    backend = _backend()
    try:
        with _sftp_server(_FSSFTP, str(remote_root)) as port:
            backend.upload_tree(src, _uri(port, "/proj"))
    except (paramiko.SSHException, OSError) as exc:
        pytest.skip(f"could not stand up local SFTP server: {exc}")

    assert (remote_root / "proj" / "a.md").read_bytes() == b"# A\n"
    assert (remote_root / "proj" / "sub" / "b.md").read_bytes() == b"bee\n"

    out = tmp_path / "out"
    with _sftp_server(_FSSFTP, str(remote_root)) as port:
        result = backend.download_tree(_uri(port, "/proj"), out)

    assert (out / "a.md").read_bytes() == b"# A\n"
    assert (out / "sub" / "b.md").read_bytes() == b"bee\n"
    assert result.files == 2


def test_real_stalled_server_times_out_not_hangs(tmp_path: Path):
    """A wedged SFTP request must raise within the timeout, never hang."""
    backend = _backend(operation_timeout=2.0)
    out = tmp_path / "out"
    try:
        with _sftp_server(_StallSFTP, str(tmp_path)) as port:
            start = time.monotonic()
            with pytest.raises(Exception) as excinfo:  # noqa: PT011
                backend.download_tree(_uri(port, "/proj"), out)
            elapsed = time.monotonic() - start
    except (paramiko.SSHException, OSError) as exc:
        pytest.skip(f"could not stand up local SFTP server: {exc}")

    # Bounded by the 2s operation timeout (+ slack), and NOT TransferCancelled
    # (nothing cancelled it — it timed out).
    assert elapsed < 20, f"transfer hung for {elapsed:.1f}s"
    assert not isinstance(excinfo.value, TransferCancelled)
