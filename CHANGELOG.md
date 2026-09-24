# Changelog

## MSTTools v1.2 — package 1.2.2

- Avoid reverse DNS during local server startup.
- Normalize Windows short paths and macOS temporary workspace paths.
- Improve integration diagnostics and cross-platform coverage.

## 1.2.1

- Prompt for the DNS hostname when menu option 16 is selected.
- Keep results visible until Enter is pressed, then redraw the menu.
- Explain invalid menu numbers and cancel empty required inputs.
- Remove sample domains from the menu and update published-install instructions.
- Add `validate`, `diff`, and SHA checksum `verify` commands with structured results and exit codes.
- Reject duplicate JSON keys, non-finite numbers, bad HTTP ports/control characters and ping options.
- Preserve unstaged Git status columns and include working-tree changes in counts.
- Add real Git, local server and TLS trust/expiry integration tests.
- Keep the default complexity threshold at 12.

## 1.2.0

### Maintenance fixes

- Split complex audit, manifest, menu, command routing and hardware routines into focused functions.
- Keep the default complexity threshold at 12; add a regression check for package functions.
- Fix the optional failure message used by `doctor` and `security` status output.
- Validate malformed dependency tables and report them without a traceback.
- Pass already-parsed arguments to legacy commands instead of parsing them a second time.
- Restore terminal color settings after each interactive command.

### Added

- Responsive Rich command center with numbered shortcuts, search and guided prompts.
- Dashboard, local audit, Python AST metrics and severity-based exit codes.
- Python / Node / Rust dependency inventory and configurable ignores.
- SHA-256 snapshots and content comparisons.
- Standalone HTML and JSON reports with explicit overwrite protection.
- Dotenv comparison, whitespace checks, JSON formatter, JWT, Base64 and UUID tools.
- TLS validation/expiry, HTTP timing/headers and concurrent localhost port checks.
- Unit/integration tests, cross-platform CI and English/Turkish documentation.

### Fixed

- Cleaner now finds generated directories instead of ignoring its own targets.
- Traversal prunes generated directories before descent and skips links.
- Local server no longer changes the process working directory.
- Git detection works from subdirectories and worktrees.
- Legacy reported errors propagate nonzero exit codes.
- Noninteractive startup prints help instead of waiting for input.
- NO_COLOR support and plain structured output.
- Obsolete numbered menu replaced by the new command center.

## 1.1.0

Original project, Git, system/network, search, diagnostics and utility toolkit.
