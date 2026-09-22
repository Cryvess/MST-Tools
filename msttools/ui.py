"""Rich terminal components. No markup interpretation of workspace data."""
import os
from pathlib import Path

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from . import __version__

console = Console(theme=Theme({'accent': '#5eead4', 'muted': '#94a3b8',
                              'good': '#a3e635', 'warn': '#fbbf24', 'bad': '#fb7185'}),
                  highlight=False, no_color='NO_COLOR' in os.environ)


def header(root=None):
    logo = Text('MST', style='bold #5eead4')
    logo.append('TOOLS', style='bold #e2e8f0')
    logo.append(f'  /  v{__version__}', style='#a3e635')
    logo.append('\nYour workspace. Understood.', style='#94a3b8')
    console.print(Panel(logo, border_style='#334155', padding=(1, 3),
                        subtitle=Text(str(root or Path.cwd()), style='#94a3b8'),
                        subtitle_align='left'))


def table(title, columns, rows):
    result = Table(title=title, title_style='bold accent', box=box.SIMPLE,
                   header_style='muted', expand=True, border_style='#334155')
    for column in columns:
        result.add_column(column, overflow='fold')
    for row in rows:
        result.add_row(*(value if isinstance(value, Text) else Text(str(value)) for value in row))
    return result


def metrics(data):
    summary = data['summary']
    grid = Table.grid(expand=True, padding=(0, 1))
    for _ in range(4):
        grid.add_column(ratio=1)
    cards = []
    for value, label, style in [(f"{data['score']}/100", 'CHECK SCORE', 'accent'),
                               (f"{summary['files']:,}", 'FILES INDEXED', 'white'),
                               (f"{summary['lines']:,}", 'TEXT LINES', 'white'),
                               (str(len(data['findings'])), 'FINDINGS', 'warn')]:
        cards.append(Panel(Text(value + '\n', style='bold ' + style) + Text(label, style='muted'),
                           border_style='#334155', padding=(1, 2)))
    grid.add_row(*cards)
    return grid


def dashboard(data, details=True):
    console.print(metrics(data))
    console.print(Text(f"\n{data['project']}  /  {data['git']['branch'] or 'local workspace'}"
                       f"  /  {data['summary']['skipped']} binary or oversized files skipped", style='muted'))
    total = sum(data['languages'].values()) or 1
    rows = []
    for i, (language, lines) in enumerate(list(data['languages'].items())[:7]):
        colors = ['#5eead4', '#818cf8', '#fbbf24', '#fb7185', '#38bdf8', '#a3e635', '#c084fc']
        percent = lines / total * 100
        rows.append([language, Text('━' * max(1, round(percent / 4)), style=colors[i]),
                     f'{percent:.1f}%', f'{lines:,}'])
    console.print(table('WORKSPACE COMPOSITION', ['Language', 'Share', '%', 'Lines'], rows))
    checks = Text()
    for check in data['checks']:
        checks.append(('  + ' if check['passed'] else '  - ') + check['name'],
                      style='good' if check['passed'] else 'warn')
    console.print(Panel(checks, title='Project foundations', border_style='#334155'))
    if details:
        findings(data['findings'][:12])
        if len(data['findings']) > 12:
            console.print(f"Showing 12 of {len(data['findings'])} findings. Use mst audit --json for all.", style='muted')
    console.print(Text(data['scope'], style='muted'))


def findings(items):
    if not items:
        console.print('No findings from the enabled checks.', style='good')
        return
    console.print(table('PRIORITIZED FINDINGS', ['Level', 'Location', 'Action'], [
        [Text(f['severity'].upper(), style={'high': 'bad', 'warning': 'warn', 'info': 'accent'}[f['severity']]),
         f"{f['file']}:{f['line']}" if f['line'] else f['file'], f['message']] for f in items]))


def result(data, title='RESULT'):
    rows = []
    for key, value in data.items():
        if isinstance(value, list):
            value = '\n'.join(str(v) for v in value) or 'None'
        elif isinstance(value, dict):
            value = '\n'.join(f'{k}: {v}' for k, v in value.items()) or 'None'
        rows.append([key.replace('_', ' ').capitalize(), value])
    console.print(table(title, ['Field', 'Value'], rows))


def menu(groups, query=''):
    panels = []
    number = 0
    for name, commands in groups:
        numbered = [(i + number + 1, command, description) for i, (command, description) in enumerate(commands)]
        number += len(commands)
        selected = [(i, command, description) for i, command, description in numbered
                    if query.lower() in (command + ' ' + description + ' ' + name).lower()]
        if not selected:
            continue
        grid = Table.grid(padding=(0, 2), expand=True)
        grid.add_column(style='accent', min_width=15)
        grid.add_column(style='muted')
        for i, command, description in selected:
            grid.add_row(Text(f'{i:02}  {command}'), Text(description))
        panels.append(Panel(grid, title=Text(name, style='bold white'), title_align='left',
                            border_style='#334155', padding=(1, 2)))
    if console.width >= 100:
        grid = Table.grid(expand=True, padding=(0, 2))
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        for i in range(0, len(panels), 2):
            grid.add_row(panels[i], panels[i + 1] if i + 1 < len(panels) else '')
        console.print(grid)
    else:
        console.print(Group(*panels))
    console.print('Number or command  /word filter  ? help  clear reset  q quit', style='muted')
    console.print('Current directory is your workspace. Run a tool to inspect it.', style='muted')
