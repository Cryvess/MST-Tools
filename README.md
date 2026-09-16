# MSTTools

A lightweight all-in-one developer utility CLI built by MST TEAM.

MSTTools analyzes the project in the directory where you run it and provides
project analysis, Git tools, networking utilities, diagnostics, system
information, security checks, and development utilities from one terminal UI.

## Install once

Clone/download this repository, open a terminal inside the repository folder,
and run:

```powershell
python -m pip install .
```

After that, open any terminal and run:

```powershell
mst
```

The colorful numbered MSTTools menu opens immediately.

## Analyze another project

MSTTools analyzes your current terminal directory:

```powershell
cd C:\Projects\MyProject
mst
```

So MSTTools does not need to be copied into every project.

## Verify installation

```powershell
mst --version
```

## Development install

If you are developing MSTTools itself:

```powershell
python -m pip install -e .
```

Changes to the package source will then be available without reinstalling it.

## Update

From the MSTTools repository:

```powershell
python -m pip install --upgrade .
```

## Uninstall

```powershell
python -m pip uninstall msttools-cli
```

## Alternative launch

```powershell
python -m msttools
```

## Main features

- Colorful numbered interactive menu
- System information, disk information, and uptime
- Project inspector, statistics, health checks, and tree
- Git status, log, info, branches, remotes, and diffs
- Project search and TODO/FIXME scanner
- Duplicate and large-file detection
- Dependency and manifest inspection
- Basic project security checks
- Localhost port scanner, ping, DNS, and HTTP checks
- Developer environment and process inspection
- Project cleaner and file hashing
- Local development server
- Dashboard, benchmark, and JSON reports

## Requirements

Python 3.9 or newer.

MSTTools supports Windows, Linux, and macOS. Some detailed system/hardware
information is Windows-specific.

## License

MIT
