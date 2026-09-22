"""Local project intelligence. Findings are heuristics, not security certification."""
import ast
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .dependencies import inspect_dependencies as dependencies
from . import __version__
from .workspace import files, settings, text_file

LANGUAGES = {'.py': 'Python', '.js': 'JavaScript', '.jsx': 'React', '.ts': 'TypeScript',
             '.tsx': 'React / TS', '.rs': 'Rust', '.go': 'Go', '.java': 'Java',
             '.cs': 'C#', '.cpp': 'C++', '.c': 'C', '.html': 'HTML', '.css': 'CSS',
             '.sh': 'Shell', '.ps1': 'PowerShell', '.sql': 'SQL', '.md': 'Markdown',
             '.json': 'JSON', '.toml': 'TOML', '.yml': 'YAML', '.yaml': 'YAML'}
SECRET_PATTERNS = [
    ('AWS access key', re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ('GitHub token', re.compile(r'\bgh[pousr]_[A-Za-z0-9_]{20,}\b')),
    ('Private key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
    ('Assigned credential', re.compile(
        r'''(?i)\b(?:api_key|secret_key|client_secret|password|auth_token)\s*[:=]\s*["']([^"'\n]{12,})["']''')),
]


def git_info(root):
    def run(*args):
        try:
            p = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=5)
            return p.stdout.rstrip('\r\n') if p.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    exists = run('rev-parse', '--is-inside-work-tree') == 'true'
    status = run('status', '--porcelain') if exists else None
    return {'available': exists, 'branch': run('branch', '--show-current') if exists else None,
            'commit': run('rev-parse', '--short', 'HEAD') if exists else None,
            'changed_files': len(status.splitlines()) if status else 0}


def complexities(source, path):
    """Approximate cyclomatic complexity per function, excluding nested scopes."""
    tree = ast.parse(source, filename=path)
    results = []
    class Decisions(ast.NodeVisitor):
        def __init__(self):
            self.score = 1
        def visit_FunctionDef(self, node):
            pass
        visit_AsyncFunctionDef = visit_FunctionDef
        visit_Lambda = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef
        def generic_visit(self, node):
            if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While,
                                 ast.ExceptHandler, ast.IfExp)):
                self.score += 1
            elif isinstance(node, ast.BoolOp):
                self.score += len(node.values) - 1
            elif isinstance(node, ast.comprehension):
                self.score += 1 + len(node.ifs)
            elif hasattr(ast, 'Match') and isinstance(node, ast.Match):
                self.score += max(0, len(node.cases) - 1)
            super().generic_visit(node)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = Decisions()
            for child in node.body:
                visitor.visit(child)
            results.append({'file': path, 'line': node.lineno, 'function': node.name,
                            'complexity': visitor.score,
                            'lines': getattr(node, 'end_lineno', node.lineno) - node.lineno + 1})
    return results


def foundation_checks(root):
    return [
        ('README', any((root / n).is_file() for n in ('README.md', 'README.rst', 'README.txt')),
         'Add installation, examples, and a screenshot to your README.'),
        ('License', any((root / n).is_file() for n in ('LICENSE', 'LICENSE.md', 'LICENSE.txt')),
         'Add a license so others know how they can use your project.'),
        ('Tests', any((root / n).is_dir() for n in ('test', 'tests', '__tests__')),
         'Add automated tests for important behavior.'),
        ('CI', (root / '.github/workflows').is_dir() or (root / '.gitlab-ci.yml').is_file(),
         'Run checks automatically in continuous integration.'),
        ('Ignore file', (root / '.gitignore').is_file(), 'Add a .gitignore for local/generated files.'),
    ]


def secret_kind(line):
    for name, pattern in SECRET_PATTERNS:
        match = pattern.search(line)
        if not match:
            continue
        if name == 'Assigned credential' and any(
            word in match[1].lower() for word in ('example', 'placeholder', 'changeme', '${', 'your_')
        ):
            continue
        return name
    return None


class ProjectAudit:
    """Accumulate one workspace review, with file IO separate from each check."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.config = settings(self.root)
        self.findings, self.functions, self.todos = [], [], []
        self.skipped, self.errors, self.largest = [], [], []
        self.languages, self.counts = Counter(), Counter()
        self.total_bytes = self.total_files = self.source_lines = 0
        self.checks = foundation_checks(self.root)

    def finding(self, severity, rule, file, line, message):
        self.findings.append(dict(severity=severity, rule=rule, file=file, line=line, message=message))

    def scan_file(self, path):
        rel = path.relative_to(self.root).as_posix()
        try:
            size = path.stat().st_size
            self.total_files += 1
            self.total_bytes += size
            self.largest.append({'file': rel, 'bytes': size})
            text = text_file(path, self.config['max_file_bytes'])
        except OSError as exc:
            self.errors.append(f'{rel}: {exc}')
            return
        if text is None:
            self.skipped.append(rel)
            return
        self.scan_text(path, rel, text)

    def scan_text(self, path, rel, text):
        lines = text.splitlines()
        language = LANGUAGES.get(path.suffix.lower(), 'Other text')
        self.languages[language] += len(lines)
        self.counts[language] += 1
        self.source_lines += len(lines)
        for number, line in enumerate(lines, 1):
            marker = re.search(r'\b(TODO|FIXME|HACK|XXX)\b[:\s]+(.+)', line)
            if marker:
                self.todos.append({'file': rel, 'line': number, 'kind': marker[1]})
            name = secret_kind(line)
            if name:
                self.finding('high', 'potential-secret', rel, number,
                             f'{name} pattern detected; value redacted. Verify and rotate if exposed.')
        if path.suffix.lower() == '.py':
            self.scan_python(rel, text)

    def scan_python(self, rel, text):
        try:
            metrics = complexities(text, rel)
        except SyntaxError as exc:
            self.finding('warning', 'python-syntax', rel, exc.lineno or 0,
                         'Python source could not be parsed by the running interpreter.')
            return
        self.functions.extend(metrics)
        threshold = self.config['complexity_threshold']
        for metric in metrics:
            if metric['complexity'] > threshold:
                self.finding('warning', 'complexity', rel, metric['line'],
                             f"{metric['function']} has complexity {metric['complexity']}; threshold is {threshold}.")

    def run(self):
        for name, passed, recommendation in self.checks:
            if not passed:
                self.finding('info', 'project-hygiene', '.', 0, recommendation)
        for path in files(self.root, self.config['ignore'], self.errors):
            self.scan_file(path)
        for err in self.errors:
            self.finding('warning', 'incomplete-scan', '.', 0, err.replace(str(self.root), '.'))
        deps = dependencies(self.root)
        for err in deps['errors']:
            self.finding('warning', 'manifest-parse', '.', 0, err.replace(str(self.root), '.'))
        return self.result(deps['dependencies'])

    def result(self, deps):
        self.findings.sort(key=lambda f: ({'high': 0, 'warning': 1, 'info': 2}[f['severity']], f['file'], f['line']))
        severity = Counter(f['severity'] for f in self.findings)
        score = max(0, 100 - min(50, severity['high'] * 15)
                    - min(30, severity['warning'] * 3) - min(20, severity['info'] * 4))
        return {'schema_version': 1, 'version': __version__,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'project': self.root.name, 'score': score,
                'summary': {'files': self.total_files, 'lines': self.source_lines, 'bytes': self.total_bytes,
                            'high': severity['high'], 'warning': severity['warning'],
                            'info': severity['info'], 'skipped': len(self.skipped)},
                'languages': dict(self.languages.most_common()), 'language_files': dict(self.counts),
                'checks': [{'name': n, 'passed': p} for n, p, _ in self.checks],
                'findings': self.findings, 'todos': self.todos,
                'functions': sorted(self.functions, key=lambda f: (-f['complexity'], f['file'], f['line'])),
                'largest': sorted(self.largest, key=lambda f: (-f['bytes'], f['file']))[:10],
                'dependencies': deps, 'git': git_info(self.root), 'skipped_files': self.skipped,
                'scope': 'Local heuristic review. UTF-8 text within size limit; links and generated directories excluded. '
                         'Score measures these checks only, not overall quality or security. Complexity is a Python AST estimate.'}


def audit(root):
    return ProjectAudit(root).run()
