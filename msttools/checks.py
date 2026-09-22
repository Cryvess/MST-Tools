"""Local syntax validation, text comparison and file integrity."""
import ast
import difflib
import hashlib
import hmac
import json
import re
from pathlib import Path

from .dependencies import tomllib
from .workspace import files, settings, text_file


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key detected')
        result[key] = value
    return result


def _invalid_number(value):
    raise ValueError('Non-finite numbers are not valid JSON')


def load_json(source):
    return json.loads(source, object_pairs_hook=_json_object, parse_constant=_invalid_number)


def validate_source(source, suffix):
    parsers = {'.json': load_json, '.toml': tomllib.loads, '.py': ast.parse}
    parsers[suffix](source)


def _parse_message(exc):
    if isinstance(exc, SyntaxError):
        return 'Invalid Python syntax for the running interpreter'
    if isinstance(exc, json.JSONDecodeError):
        return 'Invalid JSON syntax'
    if isinstance(exc, tomllib.TOMLDecodeError):
        return 'Invalid TOML syntax'
    if isinstance(exc, RecursionError):
        return 'Document nesting exceeds parser limits'
    return 'Duplicate key or unsupported JSON number'


def _validate_file(path, root, limit):
    name = path.relative_to(root).as_posix()
    try:
        source = text_file(path, limit)
        if source is None:
            return {'file': name, 'status': 'skipped', 'message': 'Not UTF-8 text or exceeds scan size limit'}
        validate_source(source, path.suffix.lower())
        return {'file': name, 'status': 'valid'}
    except OSError:
        return {'file': name, 'status': 'error', 'message': 'File could not be read'}
    except (ValueError, SyntaxError, RecursionError) as exc:
        return {'file': name, 'status': 'invalid', 'line': getattr(exc, 'lineno', None),
                'message': _parse_message(exc)}


def validate_project(root):
    root = Path(root).resolve()
    config = settings(root)
    results, errors = [], []
    for path in files(root, config['ignore'], errors):
        if path.suffix.lower() in {'.json', '.toml', '.py'}:
            results.append(_validate_file(path, root, config['max_file_bytes']))
    summary = {status: sum(r['status'] == status for r in results)
               for status in ('valid', 'invalid', 'error', 'skipped')}
    return {'checked': len(results), **summary, 'files': results,
            'errors': [message.replace(str(root), '.') for message in errors],
            'scope': 'JSON/TOML syntax and Python parsing only. No project code is executed; no schema/type checking.'}


def _diff_line(line):
    if line.endswith('\n'):
        return line
    return line + '\n\\ No newline at end of file\n'


def diff_files(before, after, context=3):
    if not 0 <= context <= 20:
        raise ValueError('Context must be between 0 and 20 lines')
    before, after = Path(before), Path(after)
    a, b = text_file(before), text_file(after)
    if a is None or b is None:
        raise ValueError('Diff requires two UTF-8 text files of at most 2 MB each')
    changes = difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True),
                                   fromfile=str(before), tofile=str(after), n=context)
    return {'identical': a == b, 'before_lines': len(a.splitlines()), 'after_lines': len(b.splitlines()),
            'diff': ''.join(_diff_line(line) for line in changes)}


def verify_file(path, expected, algorithm='sha256'):
    if algorithm not in {'sha256', 'sha384', 'sha512'}:
        raise ValueError('Choose sha256, sha384 or sha512')
    digest = hashlib.new(algorithm)
    expected = expected.strip().lower()
    if not re.fullmatch(r'[a-f0-9]{' + str(digest.digest_size * 2) + '}', expected):
        raise ValueError(f'Expected {digest.digest_size * 2} hexadecimal characters for {algorithm}')
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    actual = digest.hexdigest()
    return {'file': str(path), 'algorithm': algorithm, 'expected': expected,
            'actual': actual, 'matches': hmac.compare_digest(actual, expected)}
