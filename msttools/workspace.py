"""Bounded, deterministic workspace access shared by the v1.2 tools."""
import fnmatch
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

IGNORED = {'.git', '.hg', '.svn', '__pycache__', 'node_modules', '.venv',
           'venv', '.tox', '.nox', 'dist', 'build', 'target', '.next', '.nuxt',
           '.pytest_cache', '.mypy_cache', '.ruff_cache', '.idea', '.cache',
           'htmlcov', '.msttools'}


def linked(path):
    try:
        attrs = getattr(path.lstat(), 'st_file_attributes', 0)
        return path.is_symlink() or bool(attrs & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
    except OSError:
        return True


def settings(root):
    path = Path(root) / '.msttools.json'
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError('.msttools.json must contain an object')
    ignore = data.get('ignore', [])
    if not isinstance(ignore, list) or not all(isinstance(p, str) for p in ignore):
        raise ValueError('ignore must be an array of glob patterns')
    for key, default in [('max_file_bytes', 2_000_000), ('complexity_threshold', 12)]:
        value = data.get(key, default)
        if type(value) is not int or value < 1:
            raise ValueError(f'{key} must be a positive integer')
        data[key] = value
    data['ignore'] = ignore
    return data


def files(root, ignore=(), errors=None):
    """Prune generated directories before walking; never follow links/junctions."""
    root = Path(root).resolve()
    def excluded(path):
        name = path.relative_to(root).as_posix()
        return any(fnmatch.fnmatch(name, pat.rstrip('/')) or
                   fnmatch.fnmatch(path.name, pat.rstrip('/')) for pat in ignore)
    def failed(exc):
        if errors is not None:
            errors.append(str(exc))
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=failed):
        parent = Path(directory)
        dirs[:] = sorted(d for d in dirs if d not in IGNORED
                         and not d.endswith('.egg-info')
                         and not linked(parent / d) and not excluded(parent / d))
        for name in sorted(names):
            path = parent / name
            if not linked(path) and not excluded(path) and not name.endswith(('.pyc', '.pyo')):
                yield path


def text_file(path, limit=2_000_000):
    with Path(path).open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit or b'\0' in data:
        return None
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return None


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_text(path, content, force=False):
    """Explicit overwrite; atomic replacement, no partial report on failure."""
    path = Path(path)
    if path.exists() and not force:
        raise FileExistsError(f'{path} already exists; use --force to replace it')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.mst-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
        if force:
            os.replace(temp, path)
        else:
            # An exclusive destination also protects against a concurrent writer.
            os.link(temp, path)
            os.unlink(temp)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def write_json(path, data, force=False):
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + '\n', force)
