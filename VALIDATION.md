# MSTTools v1.2 validation

Local Windows / Python 3.12.10: **83 tests, 82 passed, one symlink test skipped**.

- All 27 menu shortcuts collect required positional inputs.
- DNS shortcut 16 resolves localhost. Blank inputs cancel; invalid numbers receive guidance.
- Successful and failed menu commands keep results visible until Enter, then redraw the menu.
- Shortcut 24 remains a cleanup preview; deletion requires explicit confirmation.
- Integration coverage includes a real temporary Git repository and local HTTP/TLS servers. Untrusted and expired certificates are rejected.
- The default Python complexity threshold remains 12 and the production-function regression check passes.
- Cross-platform GitHub Actions is configured; hosted results are available in the repository Actions tab after pushing.

Application display: MSTTools v1.2. Package metadata: msttool 1.2.1. GitHub release tag: v1.2.0.
PyPI publication is separate; an existing PyPI version cannot be replaced. Tests cover specific behavior, not every possible environment or absence of bugs.
