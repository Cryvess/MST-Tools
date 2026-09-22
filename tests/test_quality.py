import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from msttools import app, checks, cli, ui


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, source):
        path = self.root / name
        path.write_text(source, encoding='utf-8')
        return path

    def call(self, *args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = app.run(['-C', str(self.root), *args])
        return code, stream.getvalue()

    def test_validate_checks_all_formats_and_returns_failure(self):
        self.put('bad.py', 'def f(:')
        self.put('bad.json', '{"v":}')
        self.put('bad.toml', 'key = [')
        self.put('good.json', '{"v":1}')
        code, output = self.call('validate', '--json')
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)['invalid'], 3)
        self.assertEqual(json.loads(output)['valid'], 1)

    def test_validator_never_executes_python(self):
        target = self.root / 'never-created'
        self.put('script.py', 'from pathlib import Path\nPath(' + repr(str(target)) + ').touch()\n')
        self.assertEqual(checks.validate_project(self.root)['valid'], 1)
        self.assertFalse(target.exists())

    def test_duplicate_json_and_nonfinite_numbers_are_rejected(self):
        for source in ('{"a":1,"a":2}', '{"v":NaN}', '[Infinity]'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                checks.load_json(source)

    def test_skipped_files_are_not_reported_as_valid(self):
        self.put('.msttools.json', '{"max_file_bytes":2}')
        self.put('large.json', '{"value":1}')
        code, output = self.call('validate', '--json')
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output)['valid'], 0)
        self.assertGreater(json.loads(output)['skipped'], 0)

    def test_validator_redacts_source_values(self):
        marker = 'private-sensitive-text'
        self.put('bad.py', 'raise SyntaxError("' + marker)
        self.assertNotIn(marker, json.dumps(checks.validate_project(self.root)))

    def test_read_failures_return_operational_error(self):
        self.put('data.json', '{}')
        with patch('msttools.checks.text_file', side_effect=PermissionError):
            code, output = self.call('validate', '--json')
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)['error'], 1)

    def test_diff_content_and_exit_codes(self):
        self.put('a.txt', 'first\nold\n')
        self.put('b.txt', 'first\nnew\n')
        code, output = self.call('diff', 'a.txt', 'b.txt', '--json')
        self.assertEqual(code, 1)
        lines = json.loads(output)['diff'].splitlines()
        self.assertIn('-old', lines)
        self.assertIn('+new', lines)
        self.assertEqual(self.call('diff', 'a.txt', 'a.txt', '--json')[0], 0)

    def test_diff_detects_missing_newline(self):
        a, b = self.put('a.txt', 'same'), self.put('b.txt', 'same\n')
        data = checks.diff_files(a, b)
        self.assertFalse(data['identical'])
        self.assertIn('No newline at end of file', data['diff'])

    def test_diff_rejects_binary_and_invalid_context(self):
        a, b = self.put('a.bin', 'a\0b'), self.put('b.txt', 'abc')
        with self.assertRaises(ValueError):
            checks.diff_files(a, b)
        with self.assertRaises(ValueError):
            checks.diff_files(b, b, 30)

    def test_verify_all_supported_algorithms(self):
        path = self.put('data.txt', 'content')
        for algorithm in ('sha256', 'sha384', 'sha512'):
            digest = hashlib.new(algorithm, path.read_bytes()).hexdigest()
            with self.subTest(algorithm=algorithm):
                self.assertTrue(checks.verify_file(path, digest.upper(), algorithm)['matches'])
                self.assertFalse(checks.verify_file(path, '0' * len(digest), algorithm)['matches'])

    def test_bad_checksums_differ_from_mismatched_checksums(self):
        self.put('data.txt', 'content')
        self.assertEqual(self.call('verify', 'data.txt', '0' * 64, '--json')[0], 1)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.call('verify', 'data.txt', 'bad', '--json')[0], 2)

    def test_menu_has_no_sample_domain_and_prompts_for_files(self):
        with ui.console.capture() as captured:
            ui.menu(app.GROUPS)
        self.assertNotIn('example.com', captured.get())
        with patch.object(ui.console, 'input', side_effect=['a.txt', 'b.txt']):
            self.assertEqual(app._menu_arguments('diff'), ['diff', 'a.txt', 'b.txt'])

    def test_ping_rejects_options(self):
        with patch.object(cli.subprocess, 'run') as process, contextlib.redirect_stdout(io.StringIO()):
            cli.ping_host('-t')
        process.assert_not_called()

    def test_git_keeps_unstaged_status_column(self):
        response = subprocess.CompletedProcess([], 0, stdout=' M file.txt\n', stderr='')
        with patch.object(cli.subprocess, 'run', return_value=response):
            self.assertEqual(cli.run(['git', 'status', '--short']), ' M file.txt')

    def test_every_command_has_working_help(self):
        import argparse
        sub = next(a for a in app.build_parser()._actions if isinstance(a, argparse._SubParsersAction))
        for name in sub.choices:
            with self.subTest(command=name), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(app.run([name, '--help']), 0)
