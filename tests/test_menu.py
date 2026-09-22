import contextlib
import io
import unittest
from unittest.mock import patch
from msttools import app, ui

class MenuTests(unittest.TestCase):
    def test_every_number_collects_required_arguments(self):
        parser = app.build_parser()
        names = [name for _, group in app.GROUPS for name, _ in group]
        for number, name in enumerate(names, 1):
            with self.subTest(command=name), patch.object(ui.console, 'input', return_value='localhost'):
                args = app._menu_arguments(str(number))
                self.assertEqual(parser.parse_args(args).command, name)

    def test_dns_number_resolves_localhost(self):
        with patch.object(ui.console, 'input', return_value='localhost'):
            args = app._menu_arguments('16')
        self.assertEqual(args, ['dns', 'localhost'])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(app.run(args), 0)
        self.assertIn("127.0.0.1", output.getvalue())

    def test_dns_blank_cancels_before_dispatch(self):
        with patch.object(ui.console, 'input', return_value=''), self.assertRaises(ValueError):
            app._menu_arguments('16')

    def test_invalid_number_is_explained(self):
        for value in ['28', '999', '   ']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                app._menu_arguments(value)

    def test_cleanup_number_only_previews(self):
        args = app.build_parser().parse_args(app._menu_arguments('24'))
        self.assertEqual(args.command, 'clean')
        self.assertFalse(args.execute)

    def test_results_remain_visible_until_enter(self):
        for code in (0, 2):
            events = []
            with self.subTest(code=code), \
                    patch.object(app, 'run', side_effect=lambda args: events.append('run') or code), \
                    patch.object(ui.console, 'input', side_effect=lambda prompt: events.append('wait') or ''), \
                    patch.object(ui.console, 'clear', side_effect=lambda: events.append('clear')), \
                    patch.object(ui, 'header'), patch.object(ui.console, 'print'), \
                    patch.object(ui, 'menu', side_effect=lambda groups: events.append('menu')):
                app._menu_action('22')
            self.assertEqual(events, ['run', 'wait', 'clear', 'menu'])
