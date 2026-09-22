import json
import tempfile
import unittest
from pathlib import Path

from msttools import analysis, cleanup, toolkit
from msttools.workspace import files, settings, text_file, write_text


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def put(self, name, content='hello\n'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def test_walk_prunes_generated_and_configured_directories(self):
        self.put('node_modules/a.js')
        self.put('.git/config')
        self.put('vendor/a.py')
        self.put('src/main.py')
        self.assertEqual([p.relative_to(self.root).as_posix() for p in files(self.root, ['vendor'])], ['src/main.py'])

    def test_root_named_build_is_not_ignored(self):
        self.put('build/src/main.py')
        self.assertEqual(len(list(files(self.root / 'build'))), 1)

    def test_links_are_not_followed(self):
        self.put('external/data.txt')
        target = self.root / 'link'
        try:
            target.symlink_to(self.root / 'external', target_is_directory=True)
        except OSError:
            self.skipTest('Symlink permission not available')
        self.assertFalse(any('link' in p.parts for p in files(self.root)))

    def test_binary_and_oversize_not_decoded(self):
        binary = self.root / 'data.bin'
        binary.write_bytes(b'hello\0world')
        self.assertIsNone(text_file(binary))
        self.assertIsNone(text_file(self.put('large.txt', 'abcdef'), 5))

    def test_config_validation(self):
        for config in [{'ignore': 'bad'}, {'max_file_bytes': -1}, {'complexity_threshold': True}, []]:
            self.put('.msttools.json', json.dumps(config))
            with self.assertRaises(ValueError):
                settings(self.root)

    def test_exclusive_and_forced_writes(self):
        path = self.put('result.txt', 'original')
        with self.assertRaises(FileExistsError):
            write_text(path, 'replacement')
        self.assertEqual(path.read_text(), 'original')
        write_text(path, 'replacement', force=True)
        self.assertEqual(path.read_text(), 'replacement')

    def test_snapshot_detects_same_size_content_change(self):
        self.put('a.txt', 'abc')
        self.put('removed.txt')
        before = self.root / '.msttools/before.json'
        after = self.root / '.msttools/after.json'
        toolkit.snapshot(self.root, before)
        self.put('a.txt', 'xyz')
        (self.root / 'removed.txt').unlink()
        self.put('new.txt')
        toolkit.snapshot(self.root, after)
        diff = toolkit.compare_snapshots(before, after)
        self.assertEqual(diff['modified'], ['a.txt'])
        self.assertEqual(diff['removed'], ['removed.txt'])
        self.assertEqual(diff['added'], ['new.txt'])

    def test_snapshot_rejects_invalid_format(self):
        path = self.put('bad.json', '{"files": {}}')
        with self.assertRaises(ValueError):
            toolkit.compare_snapshots(path, path)

    def test_env_missing_empty_extra_never_contains_values(self):
        example = self.put('.env.example', 'A=\nB=\nC=\n')
        actual = self.put('.env', 'A=super-private-value\nB=""\nD=extra\n')
        data = toolkit.compare_env(example, actual)
        self.assertEqual(data['missing'], ['C'])
        self.assertEqual(data['empty'], ['B'])
        self.assertEqual(data['extra'], ['D'])
        self.assertNotIn('super-private-value', json.dumps(data))

    def test_env_rejects_duplicates(self):
        path = self.put('.env', 'A=one\nA=two\n')
        with self.assertRaises(ValueError):
            toolkit.env_keys(path)

    def test_cleanup_finds_nested_generated_targets_and_preserves_sources(self):
        self.put('src/main.py')
        self.put('src/__pycache__/a.pyc')
        self.put('node_modules/pkg/dist/data')
        self.put('.git/build/keep')
        self.put('.venv/build/keep')
        self.put('.coverage')
        targets = cleanup.plan(self.root)
        self.assertEqual({p.relative_to(self.root).as_posix() for p in targets},
                         {'src/__pycache__', 'node_modules', '.coverage'})
        cleanup.remove(self.root, targets)
        self.assertTrue((self.root / 'src/main.py').exists())
        self.assertTrue((self.root / '.git/build/keep').exists())

    def test_cleanup_rejects_outside_and_root(self):
        for path in (self.root, self.root.parent / 'build'):
            with self.assertRaises(ValueError):
                cleanup.remove(self.root, [path])

    def test_whitespace_locations(self):
        self.put('source.py', 'a = 1  \nb = 2')
        data = toolkit.whitespace(self.root)
        self.assertEqual(data['trailing_whitespace'], [{'file': 'source.py', 'line': 1}])
        self.assertEqual(data['missing_final_newline'], ['source.py'])

    def test_audit_secret_redaction_and_invalid_python(self):
        secret = 'AKIA' + 'A' * 16
        self.put('settings.py', 'key = "' + secret + '"\n')
        self.put('bad.py', 'def broken(:\n')
        report = analysis.audit(self.root)
        self.assertNotIn(secret, json.dumps(report))
        self.assertTrue(any(f['rule'] == 'potential-secret' for f in report['findings']))
        self.assertTrue(any(f['rule'] == 'python-syntax' for f in report['findings']))

    def test_complexity_excludes_nested_scope(self):
        metrics = analysis.complexities('def outer():\n def inner(x):\n  if x: return 1\n return inner\n', 'a.py')
        self.assertEqual({f['function']: f['complexity'] for f in metrics}, {'outer': 1, 'inner': 2})

    def test_complexity_counts_boolean_paths(self):
        metrics = analysis.complexities('def f(a,b):\n if a and b:\n  return 1\n return 0\n', 'a.py')
        self.assertEqual(metrics[0]['complexity'], 3)

    def test_dependencies_read_real_manifest_fields(self):
        self.put('pyproject.toml', '[project]\nname="demo"\ndependencies=["requests>=2"]\n[project.optional-dependencies]\ntest=["pytest"]\n')
        self.put('package.json', '{"dependencies":{"react":"^18"},"devDependencies":{"typescript":"^5"}}')
        data = analysis.dependencies(self.root)
        self.assertEqual({d['name'] for d in data['dependencies']}, {'requests', 'pytest', 'react', 'typescript'})
        self.assertFalse(data['errors'])

    def test_invalid_manifest_is_reported(self):
        self.put('package.json', '{broken')
        self.assertTrue(analysis.dependencies(self.root)['errors'])


if __name__ == '__main__':
    unittest.main()
