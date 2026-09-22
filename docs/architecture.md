# Architecture

Both `mst` and `python -m msttools` use `msttools.app:main`. The older `msttools.cli:main`
forwards to the same entry point for compatibility.

| Module | Responsibility |
| --- | --- |
| `app.py` | Arguments, exit codes, routing and interactive command center |
| `commands.py` | Independent handlers for modern commands; parsed legacy dispatch |
| `dependencies.py` | Validated manifest readers for Python, Node and Rust |
| `ui.py` | Rich panels, tables, colors and responsive layouts |
| `workspace.py` | Pruned traversal, config, bounded reads and output writes |
| `analysis.py` | Audit, AST metrics, dependencies and Git context |
| `toolkit.py` | Snapshots, dotenv, HTTP/TLS, ports, JWT and whitespace |
| `reports.py` | Escaped, standalone HTML and JSON export |
| `checks.py` | Syntax validation, local text diffs and trusted checksum comparison |
| `cleanup.py` | Discovery, boundary validation and confirmation |
| `cli.py` | Existing v1.1 diagnostics and compatibility commands |

Data flow: **arguments → workspace → structured result → terminal / JSON / HTML**.
New tool logic returns data rather than printing. Existing v1.1 tools still print directly;
migrating those entirely to structured results is future work.

## Decisions and limitations

- Rich handles terminal rendering; standard-library modules implement tools. `tomli` supports Python <3.11.
- Snapshots hash incrementally and reject files visibly changed during hashing. They do not provide
  filesystem-transaction consistency: capture a quiescent workspace for exact comparisons.
- Text reads are bounded. Large file hashing can still take time. Analysis is synchronous.
- Scores are explainable heuristics. Python syntax checks use the running interpreter's grammar.
- HTML output escapes all dynamic values and requires no external resources or JavaScript.
- Writers refuse implicit overwrites. Exclusive creation uses a hard link from a temporary file;
  filesystems without hard-link support return an operational error.
- Network operations have timeouts. Port scanning is IPv4 localhost only, at most 2,000 ports per request.
- Dependency scans read manifests as data and never execute project build scripts.
- Glob ignores are not a full Git ignore implementation.

## Tests

Tests cover content-change detection, root boundaries, directory pruning, redaction, manifest parsing,
AST metrics, dotenv errors, noninteractive behavior, structured output, exit codes, overwrite protection,
HTTP integration and TLS verification setup. Link tests skip where creation is not permitted.
CI targets three operating systems; a workflow file is not evidence of a completed hosted CI run.
