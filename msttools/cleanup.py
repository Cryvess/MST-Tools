"""Preview-first cleanup. Never traverse source-control metadata or links."""
import os
import shutil
from pathlib import Path

from .workspace import linked

TARGETS = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
           '.tox', '.nox', 'htmlcov', 'node_modules', 'dist', 'build', '.next', '.nuxt'}


def plan(root):
    root = Path(root).resolve()
    found = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        parent = Path(directory)
        keep = []
        for name in sorted(dirs):
            path = parent / name
            if linked(path) or name in {'.git', '.hg', '.svn', '.venv', 'venv', '.msttools'}:
                continue
            if name in TARGETS:
                found.append(path)
            else:
                keep.append(name)
        dirs[:] = keep
        if '.coverage' in names and not linked(parent / '.coverage'):
            found.append(parent / '.coverage')
    return found


def remove(root, targets):
    root = Path(root).resolve()
    for path in targets:
        path = Path(path)
        resolved = path.resolve()
        if linked(path) or resolved == root or root not in resolved.parents:
            raise ValueError(f'Unsafe cleanup target: {path}')
        # Reject a newly introduced symlink/junction in any ancestor as well.
        current = path
        while current != root:
            if linked(current):
                raise ValueError(f'Linked cleanup target: {path}')
            current = current.parent
        if path.name not in TARGETS | {'.coverage'}:
            raise ValueError(f'Unrecognized cleanup target: {path}')
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()


def command(execute=False):
    from . import ui
    root = Path.cwd().resolve()
    targets = plan(root)
    ui.console.print(ui.table('CLEANUP PREVIEW', ['Generated target'],
                              [[str(p.relative_to(root))] for p in targets]))
    if not targets:
        ui.console.print('No generated targets found.', style='good')
        return
    if not execute:
        ui.console.print('Preview only. To remove these targets: mst clean --execute', style='muted')
        return
    import sys
    if not sys.stdin.isatty():
        raise ValueError('Cleanup requires an interactive confirmation; no files were deleted')
    answer = ui.console.input('[warn]Delete the listed generated targets? Type DELETE to confirm: [/warn]')
    if answer != 'DELETE':
        ui.console.print('Cancelled. Nothing was deleted.', style='muted')
        return
    remove(root, targets)
    ui.console.print(f'Removed {len(targets)} generated targets.', style='good')
