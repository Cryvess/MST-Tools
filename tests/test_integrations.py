"""Local TLS handshakes, Git operations and real development-server requests."""
import contextlib
import io
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from msttools import analysis, app, cli, toolkit

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def certificate_files(root, expired=False):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.now(timezone.utc)
    end = now - timedelta(days=1) if expired else now + timedelta(days=30)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=3)).not_valid_after(end)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
            .sign(key, hashes.SHA256()))
    cert_path, key_path = root / 'cert.pem', root / 'key.pem'
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    return cert_path, key_path


def _accept_tls(listener, context, stop):
    while not stop.is_set():
        try:
            connection, _ = listener.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        try:
            with connection, context.wrap_socket(connection, server_side=True):
                pass
        except OSError:
            pass


@contextlib.contextmanager
def tls_server(cert, key):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    listener.settimeout(0.2)
    stop = threading.Event()
    thread = threading.Thread(target=_accept_tls, args=(listener, context, stop), daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1]
    finally:
        stop.set()
        listener.close()
        thread.join(timeout=3)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    @unittest.skipUnless(HAS_CRYPTO, 'Install msttool[test] to run TLS integration tests')
    def test_tls_accepts_trusted_certificate_with_matching_hostname(self):
        cert, key = certificate_files(self.root)
        context = ssl.create_default_context(cafile=str(cert))
        with tls_server(cert, key) as port, patch('msttools.toolkit.ssl.create_default_context', return_value=context):
            result = toolkit.check_tls('localhost', port)
        self.assertTrue(result['verified'])
        self.assertIn('localhost', result['dns_names'])
        self.assertGreater(result['days_remaining'], 25)

    @unittest.skipUnless(HAS_CRYPTO, 'Install msttool[test] to run TLS integration tests')
    def test_tls_rejects_untrusted_certificate(self):
        cert, key = certificate_files(self.root)
        with tls_server(cert, key) as port, self.assertRaises(ssl.SSLCertVerificationError):
            toolkit.check_tls('localhost', port)

    @unittest.skipUnless(HAS_CRYPTO, 'Install msttool[test] to run TLS integration tests')
    def test_tls_rejects_expired_certificate_even_when_trusted(self):
        cert, key = certificate_files(self.root, expired=True)
        context = ssl.create_default_context(cafile=str(cert))
        with tls_server(cert, key) as port, patch('msttools.toolkit.ssl.create_default_context', return_value=context):
            with self.assertRaises(ssl.SSLCertVerificationError):
                toolkit.check_tls('localhost', port)

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_git_real_repository_modified_and_staged_diffs(self):
        def git(*args):
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True, timeout=10)
        git('init')
        path = self.root / 'file with spaces.txt'
        path.write_text('original\n')
        git('add', '.')
        git('-c', 'user.name=MSTTools tests', '-c', 'user.email=tests@localhost',
            '-c', 'commit.gpgsign=false', 'commit', '-m', 'Initial fixture')
        path.write_text('updated\n')
        self.assertEqual(analysis.git_info(self.root)['changed_files'], 1)
        with app.working_directory(self.root), contextlib.redirect_stdout(io.StringIO()) as captured:
            cli.git_status()
            cli.git_diff()
        self.assertIn('updated', captured.getvalue())
        git('add', '.')
        with app.working_directory(self.root), contextlib.redirect_stdout(io.StringIO()) as captured:
            cli.git_diff(staged=True)
        self.assertIn('updated', captured.getvalue())

    def test_local_server_serves_selected_directory(self):
        (self.root / 'served.txt').write_text('MSTTools server integration')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        repo = Path(app.__file__).resolve().parents[1]
        process = subprocess.Popen([sys.executable, '-m', 'msttools', 'serve',
                                    '--directory', str(self.root), '--port', str(port)], cwd=repo,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            content = _get_when_ready(f'http://127.0.0.1:{port}/served.txt')
            self.assertEqual(content, b'MSTTools server integration')
            self.assertIsNone(process.poll())
        finally:
            process.terminate()
            process.wait(timeout=5)


def _get_when_ready(url):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return response.read()
        except urllib.error.URLError:
            time.sleep(0.05)
    raise AssertionError('Development server did not become ready')


if __name__ == '__main__':
    unittest.main()
