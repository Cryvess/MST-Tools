# MSTTools

A lightweight, all-in-one developer utility CLI for project analysis, Git, system diagnostics, networking, and everyday development tasks.

Install MSTTools once and launch it from any project directory with:

```bash
mst
```

MSTTools uses your current working directory as the active project, allowing you to inspect and analyze different projects without copying MSTTools into them.

## Features

### Project Analysis
- Project overview and statistics
- Project health checks
- Source line and language statistics
- Project tree viewer
- File and text search
- TODO / FIXME scanner
- Duplicate file detection
- Large file detection
- Dependency information
- Project manifest inspection
- Project cleaner
- JSON project reports

### Git Tools
- Git status
- Commit history
- Repository information
- Branch viewer
- Remote viewer
- Working-tree diff
- Staged diff
- Repository summary

### System & Diagnostics
- Detailed system information
- System summary
- System uptime
- Disk information
- Developer dashboard
- Running process viewer
- Environment information
- Developer tool detection
- MSTTools Doctor
- Basic benchmark

### Networking
- Network information
- Ping
- DNS lookup
- HTTP checks
- Localhost port scanner
- Local development HTTP server

> The port scanner is intentionally restricted to the local machine.

### Security & Utilities
- Basic project security checks
- File hashing
- Environment-variable inspection with sensitive-value masking

---

## Installation

### Install directly from GitHub

Make sure Python 3.9+ and Git are installed.

```bash
python -m pip install git+https://github.com/Cryvess/MST-Tools.git
```

After installation:

```bash
mst
```

That's it. MSTTools can now be launched from any directory.

### Install from source

Clone the repository:

```bash
git clone https://github.com/Cryvess/MST-Tools.git
cd MST-Tools
```

Install:

```bash
python -m pip install .
```

Then launch:

```bash
mst
```

---

## Usage

MSTTools analyzes the directory where you launch it.

For example:

```bash
cd path/to/my-project
mst
```

MSTTools will treat `my-project` as the active project.

You can install MSTTools once and use it across multiple projects:

```text
Project-A > mst
Project-B > mst
Project-C > mst
```

No MSTTools files need to be copied into your projects.

### Check version

```bash
mst --version
```

### Alternative launch

MSTTools can also be launched as a Python module:

```bash
python -m msttools
```

---

## Windows PATH

On some Windows Python installations, `pip` may install the `mst` command into a Scripts directory that is not included in your PATH.

If the installation succeeds but:

```text
'mst' is not recognized as an internal or external command
```

check the warning printed by `pip`. It will show the Scripts directory where `mst.exe` was installed.

Add that directory to your user `PATH`, open a new terminal, and verify the installation:

```cmd
where mst
```

Then run:

```cmd
mst
```

---

## Requirements

- Python 3.9 or newer
- Windows, Linux, or macOS
- Git recommended for Git-related functionality

Some detailed hardware and operating-system information is platform-specific.

---

## Project Health

MSTTools can perform a quick health check of the active project and detect common project components such as:

- Git repository
- README
- License
- `.gitignore`
- Dependency manifests
- Tests
- CI configuration

Project Health is intended as a quick development and maintenance overview. It is not a guarantee of software quality or security.

---

## Security

MSTTools includes lightweight security-oriented checks designed to help developers identify common project issues.

These checks are not a replacement for a professional security audit or dedicated security scanner.

Network port scanning is intentionally restricted to localhost.

---

## Development

For an editable development installation:

```bash
git clone https://github.com/Cryvess/MST-Tools.git
cd MST-Tools
python -m pip install -e .
```

You can then test changes directly with:

```bash
mst
```

---

## Uninstall

```bash
python -m pip uninstall msttools-cli
```

---

## Contributing

Bug reports, feature suggestions, and contributions are welcome.

If you find a problem or have an idea for MSTTools, feel free to open an issue or submit a pull request.

---

## License

MSTTools is licensed under the [MIT License](LICENSE).

---

**MSTTools v1.1.0**  
Developer Utilities by MST TEAM
