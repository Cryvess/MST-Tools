import base64
import contextlib
import http.server
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from msttools import __version__, app, reports, toolkit

REPO = Path(__file__).resolve().parents[1]


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def cli(self, *args, input=None):
        return subprocess.run([sys.executable, '-m', 'msttools', '-C', str(self.root), *args],
                              cwd=REPO, capture_output=True, text=True, encoding='utf-8',
                              input=input, timeout=20, env={**os.environ, 'NO_COLOR': '1', 'PYTHONIOENCODING': 'utf-8'})

    def test_version_consistent(self):
        proc = self.cli('--version')
        self.assertEqual(proc.returncode, 0)
        self.assertIn(__version__, proc.stdout)

    def test_audit_json_is_clean(self):
        proc = self.cli('audit', '--json')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['project'], self.root.name)
        self.assertNotIn('\x1b', proc.stdout)

    def test_audit_failure_threshold(self):
        proc = self.cli('audit', '--json', '--fail-on', 'info')
        self.assertEqual(proc.returncode, 1)
        self.assertTrue(json.loads(proc.stdout)['findings'])

    def test_invalid_config_returns_error_without_traceback(self):
        (self.root / '.msttools.json').write_text('[]')
        proc = self.cli('audit', '--json')
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, '')
        self.assertNotIn('Traceback', proc.stderr)

    def test_json_format_and_strict_invalid_numbers(self):
        proc = self.cli('json', '-', '--compact', '--sort-keys', input='{"b":2,"a":1}')
        self.assertEqual(proc.stdout.strip(), '{"a":1,"b":2}')
        self.assertEqual(self.cli('json', '-', input='NaN').returncode, 2)

    def test_json_no_overwrite_without_force(self):
        path = self.root / 'data.json'
        path.write_text('{"a":1}')
        proc = self.cli('json', 'data.json', '-o', 'data.json')
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(path.read_text(), '{"a":1}')

    def test_base64_utf8_round_trip(self):
        text = 'Merhaba dünya!'
        encoded = self.cli('base64', text)
        decoded = self.cli('base64', encoded.stdout.strip(), '--decode')
        self.assertEqual(decoded.stdout.strip(), text)
        self.assertEqual(self.cli('base64', '!!', '--decode').returncode, 2)

    def test_uuid_count_and_validity(self):
        import uuid
        proc = self.cli('uuid', '--count', '4')
        values = proc.stdout.splitlines()
        self.assertEqual(len(set(values)), 4)
        self.assertTrue(all(uuid.UUID(v).version == 4 for v in values))
        self.assertEqual(self.cli('uuid', '--count', '0').returncode, 2)

    def test_no_command_noninteractive_does_not_hang(self):
        proc = self.cli(input='')
        self.assertEqual(proc.returncode, 0)
        self.assertIn('usage:', proc.stdout)

    def test_legacy_invalid_hash_returns_nonzero(self):
        proc = self.cli('hash', 'nonexistent-file')
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn('\x1b', proc.stdout)

    def test_snapshot_compare_cli(self):
        self.assertEqual(self.cli('snapshot', '-o', '.msttools/a.json').returncode, 0)
        self.assertEqual(self.cli('snapshot', '-o', '.msttools/b.json').returncode, 0)
        proc = self.cli('compare', '.msttools/a.json', '.msttools/b.json', '--json')
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)['modified'], [])

    def test_report_html_contains_no_external_resources(self):
        proc = self.cli('report')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        html = (self.root / '.msttools/report.html').read_text(encoding='utf-8')
        self.assertIn('Content-Security-Policy', html)
        self.assertNotIn('<script', html)
        self.assertNotIn('src="http', html)

    def test_clean_noninteractive_refuses_deletion(self):
        path = self.root / 'build'
        path.mkdir()
        self.assertEqual(self.cli('clean', '--execute', input='').returncode, 2)
        self.assertTrue(path.exists())

    def test_working_directory_restored(self):
        previous = Path.cwd()
        with contextlib.redirect_stdout(io.StringIO()):
            app.run(['-C', str(self.root), 'uuid'])
        self.assertEqual(Path.cwd(), previous)


class ProtocolTests(unittest.TestCase):
    def test_concurrent_port_scan_detects_listening_socket(self):
        import socket
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            port = listener.getsockname()[1]
            data = toolkit.scan_ports(port, port)
            self.assertEqual(data['open_ports'][0]['port'], port)
        for start, end in [(0, 1), (2, 1), (1, 3000), (65536, 65536)]:
            with self.assertRaises(ValueError):
                toolkit.scan_ports(start, end)

    def test_report_escapes_workspace_data(self):
        from msttools.analysis import audit
        with tempfile.TemporaryDirectory() as temp:
            data = audit(Path(temp))
        data['project'] = '<script>alert(1)</script>'
        data['findings'][0]['message'] = '<img src=x onerror=alert(1)>'
        html = reports.html_report(data)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img src=x', html)
        self.assertIn('&lt;script&gt;', html)

    def test_jwt_expiry_and_no_signature_verification(self):
        def enc(value):
            return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
        data = toolkit.decode_jwt(enc({'alg': 'HS256'}) + '.' + enc({'exp': 1, 'sub': 'test'}) + '.signature')
        self.assertFalse(data['verified'])
        self.assertTrue(data['expired'])
        self.assertEqual(data['payload']['sub'], 'test')

    def test_invalid_jwt(self):
        for token in ('bad', '!.abc.xyz', 'e30.W10.x'):
            with self.assertRaises(ValueError):
                toolkit.decode_jwt(token)

    def test_http_real_local_server_success_and_404(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(404 if self.path == '/missing' else 200)
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Set-Cookie', 'secret-cookie=value')
                self.end_headers()
            def log_message(self, *args):
                pass
        with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}'
                data = toolkit.check_http(url)
                self.assertEqual(data['status'], 200)
                self.assertTrue(data['security_headers']['X-Content-Type-Options'])
                self.assertNotIn('secret-cookie', json.dumps(data))
                self.assertEqual(toolkit.check_http(url + '/missing')['status'], 404)
            finally:
                server.shutdown()
                thread.join(timeout=5)

    def test_http_rejects_credentials_and_non_http(self):
        for url in ('file:///etc/passwd', 'https://user:pass@example.com'):
            with self.assertRaises(ValueError):
                toolkit.check_http(url)

    def test_tls_keeps_certificate_verification_enabled(self):
        with patch('msttools.toolkit.ssl.create_default_context') as context, \
                patch('msttools.toolkit.socket.create_connection'):
            connection = context.return_value.wrap_socket.return_value.__enter__.return_value
            connection.getpeercert.return_value = {'notAfter': 'Jan  1 00:00:00 2030 GMT',
                                                   'issuer': (), 'subjectAltName': ()}
            connection.version.return_value = 'TLSv1.3'
            connection.cipher.return_value = ('AES', '', '')
            self.assertTrue(toolkit.check_tls('example.com')['verified'])
            context.assert_called_once_with()
            self.assertEqual(context.return_value.wrap_socket.call_args.kwargs['server_hostname'], 'example.com')


if __name__ == '__main__':
    unittest.main()
