# Contributing

1. Install with `python -m pip install -e .`.
2. Make one focused change per branch.
3. Keep tool logic separate from terminal rendering and return structured data.
4. Test meaningful behavior and failure paths with temporary workspaces or local servers.
5. Run `python -m unittest discover -s tests -v` and update command documentation.

Use Python 3.9-compatible syntax. Do not add telemetry, print credentials, silently overwrite files,
or execute scripts from inspected projects. Keep `--json` stdout machine-readable.
Do not describe heuristic scans as proof of security.

Bug reports should include OS, Python/MSTTools versions, command, expected result and a minimal reproduction.
Remove personal paths, tokens and private source before sharing output.
