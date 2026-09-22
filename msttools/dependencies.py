"""Validated dependency readers; manifests are data, never executable code."""
import json
import re
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def _mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be an object/table')
    return value


def _entry(ecosystem, name, constraint, group, manifest):
    return dict(ecosystem=ecosystem, name=name, constraint=str(constraint),
                group=group, manifest=manifest)


def _requirements(values, group, manifest):
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        raise ValueError(f'{group} dependencies must be an array of strings')
    result = []
    for value in values:
        match = re.match(r'([\w.-]+)(.*)', value.strip())
        if not match:
            raise ValueError(f'{group} contains an invalid dependency declaration')
        result.append(_entry('Python', match[1], match[2].strip() or '*', group, manifest))
    return result


def _read_requirements(path):
    values = []
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if line and not line.startswith(('#', '-')):
            values.append(line)
    group = 'development' if 'dev' in path.name else 'runtime'
    return _requirements(values, group, path.name)


def _read_python(path):
    data = tomllib.loads(path.read_text(encoding='utf-8-sig'))
    project = _mapping(data.get('project', {}), 'project')
    entries = _requirements(project.get('dependencies', []), 'runtime', path.name)
    optional = _mapping(project.get('optional-dependencies', {}), 'optional-dependencies')
    for group, values in optional.items():
        entries.extend(_requirements(values, group, path.name))
    tool = _mapping(data.get('tool', {}), 'tool')
    poetry = _mapping(tool.get('poetry', {}), 'tool.poetry')
    for name, value in _mapping(poetry.get('dependencies', {}), 'poetry.dependencies').items():
        if name != 'python':
            entries.append(_entry('Python', name, value, 'poetry', path.name))
    return entries


def _groups(data, ecosystem, names, manifest):
    _mapping(data, manifest)
    entries = []
    for group in names:
        values = _mapping(data.get(group, {}), group)
        for name, value in values.items():
            if not isinstance(value, (str, dict)):
                raise ValueError(f'{group} contains an invalid dependency constraint')
            entries.append(_entry(ecosystem, name, value, group, manifest))
    return entries


def _read_node(path):
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    return _groups(data, 'Node', ('dependencies', 'devDependencies',
                                 'peerDependencies', 'optionalDependencies'), path.name)


def _read_rust(path):
    data = tomllib.loads(path.read_text(encoding='utf-8-sig'))
    return _groups(data, 'Rust', ('dependencies', 'dev-dependencies', 'build-dependencies'), path.name)


READERS = {'requirements.txt': _read_requirements, 'requirements-dev.txt': _read_requirements,
           'pyproject.toml': _read_python, 'Cargo.toml': _read_rust, 'package.json': _read_node}


def inspect_dependencies(root):
    entries, errors = [], []
    for filename, reader in READERS.items():
        path = Path(root) / filename
        if not path.is_file():
            continue
        try:
            entries.extend(reader(path))
        except (OSError, ValueError) as exc:
            errors.append(f'{filename}: {exc}')
    return {'dependencies': entries, 'errors': errors,
            'note': 'Declared direct dependencies only; no registry or vulnerability lookup.'}
