import json
import hashlib
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from urllib.error import HTTPError

from tools import medidor_energia as medidor
from tools.testigo import bb_testigo as testigo


class DigestServer(HTTPServer):
    password = "correcta"
    realm = "device-one"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        auth = self.headers.get("Authorization", "")
        fields = {key: quoted or bare for key, quoted, bare in re.findall(r'(\w+)=(?:"([^"]*)"|([^, ]+))', auth)} if auth.startswith("Digest ") else {}
        ha1 = hashlib.sha256(f'lab:{self.server.realm}:{DigestServer.password}'.encode()).hexdigest()
        ha2 = hashlib.sha256(f'GET:{self.path}'.encode()).hexdigest()
        expected = hashlib.sha256(f'{ha1}:nonce:{fields.get("nc", "")}:{fields.get("cnonce", "")}:auth:{ha2}'.encode()).hexdigest()
        valid = (fields.get("username") == "lab" and fields.get("realm") == self.server.realm
                 and fields.get("uri") == self.path
                 and fields.get("nonce") == "nonce" and fields.get("qop") == "auth"
                 and fields.get("nc", "").isdigit() and fields.get("algorithm", "").upper() == "SHA-256"
                 and fields.get("response") == expected)
        if not valid:
            self.send_response(401)
            self.send_header("WWW-Authenticate", f'Digest realm="{self.server.realm}", nonce="nonce", algorithm=SHA-256, qop="auth"')
            self.end_headers()
            return
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", self.server.sink_url)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"apower":30,"voltage":120,"current":0.25}')

    def log_message(self, *_args):
        pass


@pytest.fixture
def digest_url(request):
    server = DigestServer(("127.0.0.1", 0), Handler)
    server.realm = getattr(request, "param", "device-one")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()


@pytest.mark.parametrize("digest_url", ["device-one", "shelly-model-123"], indirect=True)
@pytest.mark.parametrize("reader", [
    lambda url, path: medidor.lee({"tipo": "shelly", "url": url, "auth_file": path}),
    lambda url, path: testigo.lee_enchufe("shelly2", url, auth_file=path),
])
def test_digest_sha256_correct_and_wrong_key(reader, digest_url, tmp_path):
    cred = tmp_path / "shelly-auth.json"
    cred.write_text('{"usuario":"lab","contrasena":"correcta"}', encoding="utf-8")
    cred.chmod(0o600)
    result = reader(digest_url, str(cred))
    assert result["ok"] is True, result
    cred.write_text('{"usuario":"lab","contrasena":"incorrecta"}', encoding="utf-8")
    failed = reader(digest_url, str(cred))
    assert failed["ok"] is False
    assert "voltaje_v" not in failed


def test_auth_is_opt_in_and_unauthenticated_reader_unchanged():
    data = json.dumps({"apower": 30, "voltage": 120}).encode()
    assert medidor.lee({"tipo": "shelly", "url": "http://lab"}, lambda _url: data)["ok"] is True
    assert testigo.lee_enchufe("shelly2", "http://lab", abre=lambda _url: data)["ok"] is True


def test_credential_file_requires_private_mode_and_valid_json(tmp_path):
    path = tmp_path / "auth.json"
    path.write_text('{"usuario":"admin","contrasena":"local"}', encoding="utf-8")
    path.chmod(0o644)
    with pytest.raises(PermissionError):
        testigo.carga_credenciales(str(path))
    path.chmod(0o600)
    path.write_text('{"usuario":"admin"}', encoding="utf-8")
    with pytest.raises(ValueError):
        testigo.carga_credenciales(str(path))
    if os.name != "nt":
        link = tmp_path / "auth-link"
        link.symlink_to(path)
        with pytest.raises(OSError):
            testigo.carga_credenciales(str(link))


@pytest.mark.skipif(not hasattr(__import__("os"), "mkfifo"), reason="FIFO POSIX")
def test_credential_fifo_without_writer_fails_without_blocking(tmp_path):
    path = tmp_path / "auth-pipe"
    os.mkfifo(path, 0o600)
    code = "from tools.testigo.bb_testigo import carga_credenciales; carga_credenciales(__import__('sys').argv[1])"
    result = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True, timeout=1, check=False)
    assert result.returncode != 0
    assert b"regular" in result.stderr


def test_digest_verifier_rejects_uri_mismatch(digest_url):
    import hashlib
    import urllib.request

    target = "/rpc/Switch.GetStatus?id=0"
    ha1 = hashlib.sha256(b"lab:device-one:correcta").hexdigest()
    ha2 = hashlib.sha256(f"GET:{target}".encode()).hexdigest()
    cnonce, nc = "control", "00000001"
    response = hashlib.sha256(f"{ha1}:nonce:{nc}:{cnonce}:auth:{ha2}".encode()).hexdigest()
    headers = {"Authorization": f'Digest username="lab", realm="device-one", nonce="nonce", uri="/forged", response="{response}", algorithm="SHA-256", qop=auth, nc={nc}, cnonce="{cnonce}"'}
    request = urllib.request.Request(digest_url + target, headers=headers)
    with pytest.raises(HTTPError) as error:
        urllib.request.urlopen(request, timeout=2)
    assert error.value.code == 401


def test_digest_never_follows_cross_origin_redirect_with_credentials():
    seen = []

    class Sink(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.headers.get("Authorization"))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args):
            pass

    sink = HTTPServer(("127.0.0.1", 0), Sink)
    sink_thread = threading.Thread(target=sink.serve_forever, daemon=True)
    sink_thread.start()

    source = DigestServer(("127.0.0.1", 0), Handler)
    source.sink_url = f"http://127.0.0.1:{sink.server_port}/collect"
    source_thread = threading.Thread(target=source.serve_forever, daemon=True)
    source_thread.start()
    try:
        with pytest.raises(HTTPError):
            testigo.abre_http(f"http://127.0.0.1:{source.server_port}/redirect", "lab", "correcta")
        assert seen == []
    finally:
        source.shutdown()
        sink.shutdown()
        source_thread.join()
        sink_thread.join()
