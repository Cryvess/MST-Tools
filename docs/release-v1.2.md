# MSTTools v1.2

MSTTools v1.2 turns the v1.1 command-line toolkit into an interactive project command center. Run `mst` inside a project to explore its files, review local findings, compare changes, and export a report.

## Highlights

- **27 numbered tools:** a colorful, responsive menu with command filtering and guided inputs. Results stay visible until you press Enter.
- **Project insight:** language and file metrics, prioritized audit findings, Python complexity estimates, and direct Python/Node/Rust dependency inventories.
- **Changes and integrity:** SHA-256 workspace snapshots, added/removed/modified file detection, text diffs, and SHA-256/384/512 checksum verification.
- **Configuration and syntax:** missing or empty dotenv keys, whitespace checks, strict JSON formatting, and JSON/TOML/Python syntax validation.
- **Shareable results:** offline HTML reports and structured JSON for automation.
- **Developer diagnostics:** HTTP response checks, verified TLS certificates, local TCP port checks, Git utilities, JWT inspection, Base64, and UUIDs.

## Reliability improvements since v1.1

- DNS menu option 16 now asks for a hostname; empty input cancels cleanly.
- Invalid menu numbers receive guidance instead of a parser error.
- Menu option 24 previews cleanup; deletion requires an explicit command and confirmation.
- Avoid reverse DNS during local HTTP server startup, fixing delays on macOS.
- Normalize workspace paths, including Windows short paths and macOS temporary directories.
- Fixed Git status column handling and Windows redirected-output character errors.
- Refactored complex functions while retaining the default complexity threshold of 12.
- Traversal skips links and generated directories. Reports and snapshots require explicit overwrite permission.
- Commands propagate failures through meaningful exit codes. Direct command-line usage remains suitable for scripts and does not pause for Enter.

## Installation and upgrade

Package name: **msttool**. Terminal command: **mst**. Application label: **MSTTools v1.2**. The updated package metadata is **1.2.2**.

```console
python -m pip install --upgrade msttool
mst
```

PyPI currently provides 1.2.1. The attached 1.2.2 packages additionally fix loopback-server startup and workspace paths across platforms. To install the exact GitHub release, download and extract the attached source ZIP, open its `MSTTools` folder, and install from source:

```console
python -m pip install --upgrade .
```

If you previously installed `msttools-cli`, uninstall that old distribution before installing `msttool`; both provide the same `mst` command:

```console
python -m pip uninstall msttools-cli
python -m pip install --upgrade .
```

Open a terminal in the project you want to inspect, then run `mst`. Use `python -m msttools` if your Python scripts directory is not on PATH.

## Validation and scope

The release test suite covers menu inputs, pause-and-return behavior, temporary Git repositories, local HTTP/TLS servers, file comparisons, and checksum verification. See [VALIDATION.md](https://github.com/Cryvess/MST-Tools/blob/v1.2.0/VALIDATION.md) and the repository Actions tab for results.

Project analysis stays local. Network commands contact the destination you choose. Audit findings and scores are heuristics, not security certification; dependency inventory is not a vulnerability scan, and JWT inspection does not verify signatures.

## Documentation

- [English guide](https://github.com/Cryvess/MST-Tools/blob/v1.2.0/README.md)
- [Türkçe kılavuz](https://github.com/Cryvess/MST-Tools/blob/v1.2.0/README.tr.md)
- [Changelog](https://github.com/Cryvess/MST-Tools/blob/v1.2.0/CHANGELOG.md)

**Full comparison:** https://github.com/Cryvess/MST-Tools/compare/v1.1.0...v1.2.0
