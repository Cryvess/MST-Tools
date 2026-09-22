"""One handler per command; routing contains no argument-dependent branch chain."""
import base64
import json
import os
import sys
import uuid
from contextlib import nullcontext
from pathlib import Path

from . import analysis, reports, toolkit, ui, checks
from .workspace import write_text


def emit(data, args):
    if getattr(args, 'json', False):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        ui.result(data, args.command.upper())


def _present_analysis(data, args):
    if getattr(args, 'json', False):
        emit(data, args)
    else:
        ui.header(Path.cwd())
        ui.dashboard(data)


def _present_report(data, args):
    reports.export(data, args.output, args.force)
    ui.console.print('Report saved: ' + str(Path(args.output).resolve()), style='good', markup=False)


def _present_complexity(data, args):
    metrics = data['functions'][:args.limit]
    if args.json:
        emit({'functions': metrics, 'scope': data['scope']}, args)
        return
    rows = [[f['function'], f"{f['file']}:{f['line']}", f['complexity'], f['lines']] for f in metrics]
    ui.console.print(ui.table('PYTHON COMPLEXITY', ['Function', 'Location', 'Complexity', 'Lines'], rows))


def analyze(args):
    status = nullcontext() if getattr(args, 'json', False) else ui.console.status('Reading workspace…')
    with status:
        data = analysis.audit(Path.cwd())
    presenter = {'report': _present_report, 'complexity': _present_complexity}.get(args.command, _present_analysis)
    presenter(data, args)
    threshold = getattr(args, 'fail_on', 'none')
    if threshold == 'none':
        return 0
    levels = ['high', 'warning', 'info'][:['high', 'warning', 'info'].index(threshold) + 1]
    return int(any(f['severity'] in levels for f in data['findings']))


def deps(args):
    data = analysis.dependencies(Path.cwd())
    if args.json:
        emit(data, args)
    else:
        rows = [[d['ecosystem'], d['name'], d['constraint'], d['group']] for d in data['dependencies']]
        ui.console.print(ui.table('DEPENDENCY INVENTORY', ['Ecosystem', 'Package', 'Constraint', 'Group'], rows))
        for err in data['errors']:
            ui.console.print(err, style='bad', markup=False)
        ui.console.print(data['note'], style='muted')
    return 2 if data['errors'] else 0


def snapshot(args):
    emit(toolkit.snapshot(Path.cwd(), args.output, args.force), args)
    return 0


def compare(args):
    data = toolkit.compare_snapshots(args.before, args.after)
    emit(data, args)
    return int(any(data[key] for key in ('added', 'removed', 'modified')))


def envcheck(args):
    data = toolkit.compare_env(args.example, args.actual)
    emit(data, args)
    return int(bool(data['missing'] or data['empty']))


def http(args):
    data = toolkit.check_http(args.url)
    emit(data, args)
    return int(data['status'] >= 400)


def ports(args):
    emit(toolkit.scan_ports(args.start, args.end), args)
    return 0


def tls(args):
    data = toolkit.check_tls(args.host, args.port)
    emit(data, args)
    return int(data['days_remaining'] < 14)


def whitespace(args):
    data = toolkit.whitespace(Path.cwd())
    emit(data, args)
    if data['errors']:
        return 2
    return int(bool(data['trailing_whitespace'] or data['missing_final_newline']))


def format_json(args):
    source = sys.stdin.read() if args.file == '-' else Path(args.file).read_text(encoding='utf-8-sig')
    data = checks.load_json(source)
    formatted = json.dumps(data, indent=None if args.compact else 2,
                           separators=(',', ':') if args.compact else None,
                           sort_keys=args.sort_keys, ensure_ascii=False, allow_nan=False) + '\n'
    if args.output:
        write_text(args.output, formatted, args.force)
        ui.console.print('JSON saved: ' + args.output, style='good', markup=False)
    else:
        print(formatted, end='')
    return 0


def jwt(args):
    source = sys.stdin.read() if args.token == '-' else args.token
    emit(toolkit.decode_jwt(source), args)
    return 0


def base64_text(args):
    source = sys.stdin.read() if args.text == '-' else args.text
    if args.decode:
        print(base64.b64decode(source.strip(), validate=True).decode('utf-8'))
    else:
        print(base64.b64encode(source.encode('utf-8')).decode('ascii'))
    return 0


def uuid_values(args):
    for _ in range(args.count):
        print(uuid.uuid4())
    return 0


def clean(args):
    from .cleanup import command
    command(args.execute)
    return 0


def validate(args):
    data = checks.validate_project(Path.cwd())
    if args.json:
        emit(data, args)
    else:
        ui.console.print(ui.table('PROJECT VALIDATION', ['File', 'Status', 'Details'],
                                 [[r['file'], r['status'], r.get('message', '')] for r in data['files']]))
        ui.console.print(f"Checked {data['checked']} files: {data['valid']} valid, {data['invalid']} invalid, "
                         f"{data['skipped']} skipped, {data['error']} unreadable.", markup=False)
        ui.console.print(data['scope'], style='muted')
        for error in data['errors']:
            ui.console.print(error, style='bad', markup=False)
    if data['errors'] or data['error']:
        return 2
    return int(bool(data['invalid'] or data['skipped']))


def diff(args):
    data = checks.diff_files(args.before, args.after, args.context)
    if args.json:
        emit(data, args)
    elif data['identical']:
        ui.console.print('Files have identical text content.', style='good')
    else:
        from rich.syntax import Syntax
        ui.console.print(Syntax(data['diff'], 'diff', theme='monokai', word_wrap=True))
    return int(not data['identical'])


def verify(args):
    data = checks.verify_file(args.file, args.expected, args.algorithm)
    emit(data, args)
    return int(not data['matches'])


def legacy_command(args):
    from . import cli
    cli.configure_colors(not args.no_color and ui.console.is_terminal and 'NO_COLOR' not in os.environ)
    cli._errors = 0
    cli.run_args(args)
    return 2 if cli._errors else 0


HANDLERS = {'audit': analyze, 'dashboard': analyze, 'complexity': analyze, 'report': analyze,
            'deps': deps, 'snapshot': snapshot, 'compare': compare, 'envcheck': envcheck,
            'http': http, 'ports': ports, 'tls': tls, 'whitespace': whitespace,
            'json': format_json, 'jwt': jwt, 'base64': base64_text, 'uuid': uuid_values, 'clean': clean,
            'validate': validate, 'diff': diff, 'verify': verify}


def dispatch(args, raw=None):
    return HANDLERS.get(args.command, legacy_command)(args)
