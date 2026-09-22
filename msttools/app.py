"""v1.2 entry point and command center; v1.1 commands remain available."""
import argparse
import binascii
import os
import shlex
import sys
from contextlib import contextmanager
from pathlib import Path

from .commands import dispatch
from . import ui, __version__

GROUPS = [
    ('01 / WORKSPACE', [('dashboard', 'Project overview & language bars'), ('audit', 'Prioritized code & hygiene findings'),
                         ('complexity', 'Python function complexity'), ('deps', 'Python, Node & Rust dependencies'),
                         ('todo', 'Find TODO / FIXME markers'), ('tree', 'Browse project structure')]),
    ('02 / COMPARE & EXPORT', [('snapshot', 'Save file hashes for later comparison'), ('compare', 'Added, removed & modified files'),
                              ('report', 'Shareable HTML or JSON review'), ('envcheck', 'Find missing configuration keys'),
                              ('whitespace', 'Trailing spaces & missing newlines'), ('duplicates', 'Find identical files')]),
    ('03 / NETWORK & SYSTEM', [('http', 'HTTP timing & response headers'), ('tls', 'Verified certificate & expiry'),
                              ('ports', 'Find local development servers'), ('dns', 'Resolve hostnames'),
                              ('system', 'Machine & hardware information'), ('doctor', 'Environment diagnostics')]),
    ('04 / DEVELOPER UTILITIES', [('json', 'Validate & format JSON'), ('jwt', 'Inspect token claims locally'),
                                 ('base64', 'Encode or decode text'), ('uuid', 'Generate random UUIDs'),
                                 ('git', 'Status, history & diffs'), ('clean', 'Preview generated-file cleanup')]),
    ('05 / QUALITY & INTEGRITY', [('validate', 'Check JSON, TOML & Python syntax'),
                                 ('diff', 'Compare two text files line by line'),
                                 ('verify', 'Verify a file against a trusted checksum')]),
]


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def build_parser():
    from .cli import build_parser as legacy_parser
    parser = legacy_parser()
    parser.description = f'MSTTools v{__version__} — Your workspace. Understood.'
    parser.add_argument('--path', '-C', type=Path, default=Path.cwd(), help='Workspace (put before command)')
    parser.add_argument('--no-color', action='store_true', help='Disable terminal colors')
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    commands = sub.choices
    for name in ('dashboard', 'deps', 'http', 'ports'):
        commands[name].add_argument('--json', action='store_true', help='Machine-readable JSON')
    commands['report'].add_argument('--force', action='store_true', help='Replace an existing report')
    commands['report'].set_defaults(output='.msttools/report.html')
    audit = sub.add_parser('audit', help='Local code, secrets and project hygiene review')
    audit.add_argument('--json', action='store_true')
    audit.add_argument('--fail-on', choices=['high', 'warning', 'info', 'none'], default='high')
    complexity = sub.add_parser('complexity', help='Rank Python functions by complexity')
    complexity.add_argument('--json', action='store_true')
    complexity.add_argument('--limit', type=int, choices=range(1, 501), default=20, metavar='1..500')
    snap = sub.add_parser('snapshot', help='Save SHA-256 workspace snapshot')
    snap.add_argument('--output', '-o', default='.msttools/snapshot.json')
    snap.add_argument('--force', action='store_true')
    snap.add_argument('--json', action='store_true')
    compare = sub.add_parser('compare', help='Compare two snapshots; exit 1 when different')
    compare.add_argument('before')
    compare.add_argument('after')
    compare.add_argument('--json', action='store_true')
    env = sub.add_parser('envcheck', help='Compare dotenv keys without revealing values')
    env.add_argument('--example', default='.env.example')
    env.add_argument('--actual', default='.env')
    env.add_argument('--json', action='store_true')
    tls = sub.add_parser('tls', help='Validate TLS certificate and inspect expiry')
    tls.add_argument('host')
    tls.add_argument('--port', type=int, default=443)
    tls.add_argument('--json', action='store_true')
    whitespace = sub.add_parser('whitespace', help='Check whitespace without changing source files')
    whitespace.add_argument('--json', action='store_true')
    formatter = sub.add_parser('json', help='Validate/format JSON; use - for stdin')
    formatter.add_argument('file')
    formatter.add_argument('--output', '-o')
    formatter.add_argument('--sort-keys', action='store_true')
    formatter.add_argument('--compact', action='store_true')
    formatter.add_argument('--force', action='store_true')
    jwt = sub.add_parser('jwt', help='Decode JWT (signature NOT verified); use - for stdin')
    jwt.add_argument('token')
    jwt.add_argument('--json', action='store_true')
    b64 = sub.add_parser('base64', help='Encode/decode UTF-8 text; use - for stdin')
    b64.add_argument('text')
    b64.add_argument('--decode', '-d', action='store_true')
    uid = sub.add_parser('uuid', help='Generate random UUID v4 values')
    uid.add_argument('--count', type=int, choices=range(1, 1001), default=1, metavar='1..1000')
    sub.add_parser('menu', help='Open the interactive command center')
    _quality_parsers(sub)
    parser.epilog = 'Run mst to open the command center. Use mst COMMAND --help for tool options.'
    return parser


def _quality_parsers(sub):
    validator = sub.add_parser('validate', help='Validate project JSON, TOML and Python syntax')
    validator.add_argument('--json', action='store_true')
    diff = sub.add_parser('diff', help='Compare the contents of two UTF-8 text files')
    diff.add_argument('before')
    diff.add_argument('after')
    diff.add_argument('--context', type=int, choices=range(21), default=3, metavar='0..20')
    diff.add_argument('--json', action='store_true')
    verify = sub.add_parser('verify', help='Verify a file against a known SHA checksum')
    verify.add_argument('file')
    verify.add_argument('expected', help='Trusted hexadecimal digest')
    verify.add_argument('--algorithm', choices=['sha256', 'sha384', 'sha512'], default='sha256')
    verify.add_argument('--json', action='store_true')


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in '\"\'':
        return value[1:-1]
    return value


def _menu_arguments(line):
    # Preserve Windows backslashes and quoted paths.
    parts = [_unquote(value) for value in shlex.split(line, posix=False)]
    if not parts:
        raise ValueError('Enter a menu number or command')
    names = [name for _, entries in GROUPS for name, _ in entries]
    if parts[0].isdigit():
        if not 1 <= int(parts[0]) <= len(names):
            raise ValueError(f'Choose a menu number from 1 to {len(names)}')
        parts[0] = names[int(parts[0]) - 1]
    if len(parts) == 1:
        _prompt_arguments(parts)
    return parts


def _prompt_arguments(parts):
    prompts = {'http': ['URL'], 'tls': ['Hostname'], 'dns': ['Hostname or IP address'],
               'json': ['JSON file path'],
               'jwt': ['JWT token (decoded locally)'], 'base64': ['Text to encode'],
               'compare': ['Before snapshot path', 'After snapshot path'],
               'diff': ['First text file', 'Second text file'],
               'verify': ['File to verify', 'Expected SHA-256 checksum']}
    if parts[0] == 'git':
        parts.append('status')
    for prompt in prompts.get(parts[0], []):
        value = ui.console.input(prompt + ' > ').strip().strip('"')
        if not value:
            raise ValueError('Input cancelled: a value is required')
        parts.append(value)


def _menu_action(line):
    if not line:
        return
    if line.startswith('/'):
        ui.menu(GROUPS, line[1:])
        return
    if line in ('?', 'help', 'clear', 'menu'):
        if line == 'clear':
            ui.console.clear()
            ui.header()
        ui.menu(GROUPS)
        ui.console.print('All v1.1 commands remain available. Try: --help or COMMAND --help.', style='muted')
        return
    code = run(_menu_arguments(line))
    if code:
        ui.console.print(f'Command completed with exit code {code}.', style='warn')
    ui.console.input('\n[muted]Devam etmek için Enter\'a bas…[/muted] ')
    ui.console.clear()
    ui.header()
    ui.menu(GROUPS)


def command_center():
    ui.header()
    ui.menu(GROUPS)
    while True:
        try:
            line = ui.console.input('\n[accent]mst[/accent] [muted]›[/muted] ').strip()
            if line.lower() in ('q', 'quit', 'exit', '0', '00'):
                return 0
            _menu_action(line)
        except (EOFError, KeyboardInterrupt):
            ui.console.print('\nSession closed.', style='muted')
            return 0
        except ValueError as exc:
            ui.console.print(str(exc), style='bad', markup=False)


def run(argv=None):
    raw = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    original_no_color = ui.console.no_color
    try:
        args = parser.parse_args(raw)
        if args.no_color:
            ui.console.no_color = True
        root = args.path.expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f'Workspace is not a directory: {root}')
        with working_directory(root):
            if args.command in (None, 'menu'):
                if not sys.stdin.isatty():
                    parser.print_help()
                    return 0
                return command_center()
            return dispatch(args, raw)
    except SystemExit as exc:
        return int(exc.code or 0)
    except KeyboardInterrupt:
        print('Cancelled.', file=sys.stderr)
        return 130
    except (OSError, ValueError, binascii.Error, UnicodeError, RecursionError) as exc:
        # stderr stays separate from structured stdout.
        print(f'MSTTools: {exc}', file=sys.stderr)
        return 2
    finally:
        ui.console.no_color = original_no_color


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    raise SystemExit(run())
