"""Behavior regressions for the v1.2 complexity cleanup."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from msttools import analysis, app, cli, commands, ui


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def capture_legacy(self, function, *args, **kwargs):
        stream = io.StringIO()
        with app.working_directory(self.root), contextlib.redirect_stdout(stream):
            function(*args, **kwargs)
        return stream.getvalue()

    def test_security_runs_without_git_and_does_not_print_secret(self):
        token = 'AKIA' + 'Z' * 16
        self.put('settings.py', 'key = "' + token + '"\n')
        with patch.object(cli, 'run', return_value=''):
            output = self.capture_legacy(cli.security_check)
        self.assertIn('settings.py:1', output)
        self.assertNotIn(token, output)
        self.assertIn('Git tracking checks skipped', output)

    def test_doctor_handles_present_env_without_parameter_error(self):
        self.put('.env', 'NAME=value\n')
        with patch.object(cli, 'run', return_value=''):
            output = self.capture_legacy(cli.doctor)
        self.assertIn('.env detected in project root.', output)

    def test_status_line_selects_the_correct_message(self):
        good = self.capture_legacy(cli.status_line, True, 'present', 'absent')
        bad = self.capture_legacy(cli.status_line, False, 'present', 'absent')
        self.assertIn('present', good)
        self.assertNotIn('absent', good)
        self.assertIn('absent', bad)
        self.assertNotIn('present', bad)

    def test_search_plain_text_does_not_interpret_regex(self):
        self.put('src/a.py', 'a.b\naxb\nA.B\n')
        output = self.capture_legacy(cli.search_project, 'a.b', case_sensitive=True)
        self.assertIn('1 match(es)', output)
        self.assertNotIn('axb', output)

    def test_search_regex_extension_and_limit(self):
        self.put('a.py', 'name1\nname2\nname3\n')
        self.put('b.txt', 'name4\n')
        output = self.capture_legacy(cli.search_project, r'name\d', regex=True, extension='py', max_results=2)
        self.assertIn('a.py:2', output)
        self.assertNotIn('a.py:3', output)
        self.assertNotIn('b.txt', output)
        self.assertIn('limit reached', output)

    def test_invalid_regex_is_reported_without_exception(self):
        output = self.capture_legacy(cli.search_project, '[', regex=True)
        self.assertIn('Invalid regular expression', output)

    def test_duplicate_groups_compare_content_not_only_size(self):
        self.put('a.txt', 'same')
        self.put('b.txt', 'same')
        self.put('c.txt', 'diff')
        with app.working_directory(self.root):
            groups = list(cli._duplicate_groups())
        self.assertEqual([{p.name for p in group} for group in groups], [{'a.txt', 'b.txt'}])

    def test_malformed_dependency_tables_are_structured_errors(self):
        bad_inputs = [('package.json', 'null'), ('package.json', '{"dependencies":[]}'),
                      ('pyproject.toml', '[project]\ndependencies="wrong"\n'),
                      ('pyproject.toml', '[project.optional-dependencies]\ntest=[1]\n'),
                      ('Cargo.toml', 'dependencies="wrong"\n')]
        for name, content in bad_inputs:
            with self.subTest(name=name, content=content):
                self.put(name, content)
                result = analysis.dependencies(self.root)
                self.assertTrue(result['errors'])
                (self.root / name).unlink()

    def test_rust_and_poetry_dependency_groups(self):
        self.put('Cargo.toml', '[dependencies]\nserde={version="1",features=["derive"]}\n')
        self.put('pyproject.toml', '[tool.poetry.dependencies]\npython="^3.9"\nrequests="^2"\n')
        result = analysis.dependencies(self.root)
        self.assertFalse(result['errors'])
        self.assertEqual({d['name'] for d in result['dependencies']}, {'serde', 'requests'})

    def test_audit_honors_complexity_threshold_in_external_projects(self):
        self.put('branch.py', 'def choose(a, b):\n if a and b:\n  return 1\n return 0\n')
        self.put('.msttools.json', '{"complexity_threshold":2}')
        findings = analysis.audit(self.root)['findings']
        complexity = [f for f in findings if f['rule'] == 'complexity']
        self.assertEqual(len(complexity), 1)
        self.assertIn('complexity 3; threshold is 2', complexity[0]['message'])

    def test_no_color_does_not_leak_into_next_command(self):
        original = ui.console.no_color
        with contextlib.redirect_stdout(io.StringIO()):
            code = app.run(['-C', str(self.root), '--no-color', 'uuid'])
        self.assertEqual(code, 0)
        self.assertEqual(ui.console.no_color, original)

    def test_legacy_receives_parsed_arguments_without_reparsing(self):
        argv = ['-C', str(self.root), 'search', 'a b', '--extension', 'py', '--max-results', '2']
        with patch.object(cli, 'search_project') as search, contextlib.redirect_stdout(io.StringIO()):
            code = app.run(argv)
        self.assertEqual(code, 0)
        search.assert_called_once_with('a b', False, 'py', False, 2)

    def test_project_subcommand_and_git_arguments_survive_dispatch(self):
        with patch.object(cli, 'project_stats') as stats, contextlib.redirect_stdout(io.StringIO()):
            code = app.run(['-C', str(self.root), 'project', 'stats'])
        self.assertEqual(code, 0)
        stats.assert_called_once_with()
        with patch.object(cli, 'git_log') as log, contextlib.redirect_stdout(io.StringIO()):
            code = app.run(['-C', str(self.root), 'git', 'log', '--limit', '7'])
        self.assertEqual(code, 0)
        log.assert_called_once_with(7)

    def test_windows_hardware_sections_accept_missing_optional_values(self):
        helpers = [getattr(cli, name) for name in dir(cli) if name.startswith('_system_')]
        with patch.object(cli, 'get_cim', return_value={}), \
                patch.object(cli, 'get_cim_all', return_value=[{}]), \
                patch.object(cli, 'powershell', return_value=''):
            for helper in helpers:
                with self.subTest(section=helper.__name__):
                    self.capture_legacy(helper)

    def test_menu_keeps_windows_paths_and_numbered_shortcuts(self):
        parts = app._menu_arguments(r'json "C:\My Project\data.json" --sort-keys')
        self.assertEqual(parts, ['json', r'C:\My Project\data.json', '--sort-keys'])
        self.assertEqual(app._menu_arguments('01'), ['dashboard'])
        self.assertEqual(app._menu_arguments('git'), ['git', 'status'])

    def test_menu_filters_and_guides_required_arguments(self):
        with patch.object(ui, 'menu') as menu:
            app._menu_action('/network')
        menu.assert_called_once_with(app.GROUPS, 'network')
        with patch.object(ui.console, 'input', return_value='example.com'):
            self.assertEqual(app._menu_arguments('tls'), ['tls', 'example.com'])

    def test_menu_continues_after_bad_input(self):
        with patch.object(ui, 'header'), patch.object(ui, 'menu'), \
                patch.object(ui.console, 'input', side_effect=['json "unfinished', 'q']), \
                patch.object(ui.console, 'print'):
            self.assertEqual(app.command_center(), 0)

    def test_production_functions_respect_default_complexity_budget(self):
        package = Path(analysis.__file__).parent
        over_budget = []
        for path in package.glob('*.py'):
            metrics = analysis.complexities(path.read_text(encoding='utf-8'), path.name)
            over_budget.extend(f for f in metrics if f['complexity'] > 12)
        self.assertEqual(over_budget, [])


if __name__ == '__main__':
    unittest.main()
