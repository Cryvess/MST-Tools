import argparse
import hashlib
import http.server
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# MSTTools
# MST TEAM
# Developer Utility CLI
# ============================================================

VERSION = "1.1.0"

RESET = "\033[0m"
BLUE = "\033[94m"
LIGHT_BLUE = "\033[96m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;208m"
GREEN = "\033[92m"
RED = "\033[91m"
WHITE = "\033[97m"
GRAY = "\033[90m"
MAGENTA = "\033[95m"

if os.name == "nt":
    os.system("")

IGNORED_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", ".nox",
    "node_modules", "venv", ".venv", "env", ".env",
    "dist", "build", "target", ".idea", ".vscode",
    ".coverage", "htmlcov", ".cache", ".next", ".nuxt",
}

LANGUAGES = {
    ".py": "Python", ".pyw": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript React",
    ".jsx": "JavaScript React",
    ".java": "Java", ".c": "C", ".h": "C/C++ Header",
    ".cc": "C++", ".cpp": "C++", ".cxx": "C++",
    ".hpp": "C++ Header", ".cs": "C#", ".go": "Go", ".rs": "Rust",
    ".php": "PHP", ".rb": "Ruby", ".swift": "Swift",
    ".kt": "Kotlin", ".kts": "Kotlin", ".lua": "Lua",
    ".dart": "Dart", ".r": "R", ".scala": "Scala",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".sass": "Sass", ".less": "Less",
    ".json": "JSON", ".xml": "XML", ".yaml": "YAML",
    ".yml": "YAML", ".toml": "TOML", ".ini": "INI",
    ".sql": "SQL", ".sh": "Shell", ".bash": "Shell",
    ".zsh": "Shell", ".fish": "Shell", ".bat": "Batch",
    ".cmd": "Batch", ".ps1": "PowerShell", ".psm1": "PowerShell",
    ".dockerfile": "Dockerfile", ".proto": "Protocol Buffers",
    ".graphql": "GraphQL", ".gql": "GraphQL", ".md": "Markdown",
}

CLEAN_TARGETS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".nox", ".coverage", "htmlcov", "node_modules",
    "dist", "build", "target", ".next", ".nuxt",
}

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 25: "SMTP", 53: "DNS", 80: "HTTP",
    110: "POP3", 135: "MS RPC", 139: "NetBIOS", 143: "IMAP",
    443: "HTTPS", 445: "SMB", 3000: "Dev Server", 3306: "MySQL",
    5000: "Flask/Dev", 5173: "Vite", 5432: "PostgreSQL",
    5672: "RabbitMQ", 6379: "Redis", 8000: "Dev Server",
    8080: "HTTP Proxy/Dev", 8443: "HTTPS Dev", 8888: "Jupyter",
    27017: "MongoDB",
}

SECRET_WORDS = (
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "access_key", "private_key", "client_secret", "auth_token",
    "credential", "credentials", "jwt", "bearer",
)

TODO_PATTERNS = ("TODO", "FIXME", "XXX", "HACK", "BUG", "NOTE")

TEXT_EXTENSIONS = set(LANGUAGES) | {
    ".txt", ".cfg", ".conf", ".env.example", ".gitignore",
    ".gitattributes", ".editorconfig", ".lock",
}

# ============================================================
# UI
# ============================================================

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def line(char="─", length=72, color=BLUE):
    print(color + char * length + RESET)


def title(text):
    print()
    line()
    print(f"{BLUE}  {text}{RESET}")
    line()


def success(text):
    print(f"{GREEN}[+]{RESET} {text}")


def warning(text):
    print(f"{ORANGE}[!]{RESET} {text}")


def error(text):
    print(f"{RED}[-]{RESET} {text}")


def info(text):
    print(f"{LIGHT_BLUE}[*]{RESET} {text}")


def label(name, value):
    print(f"{YELLOW}{name:<26}{RESET} {WHITE}{value}{RESET}")


def section(text):
    print()
    print(f"{BLUE}--- {text} ---{RESET}")


def show_logo():
    print(f"""
{BLUE}███╗   ███╗ ███████╗ ████████╗
████╗ ████║ ██╔════╝ ╚══██╔══╝
██╔████╔██║ ███████╗    ██║
██║╚██╔╝██║ ╚════██║    ██║
██║ ╚═╝ ██║ ███████║    ██║
╚═╝     ╚═╝ ╚══════╝    ╚═╝{RESET}

{LIGHT_BLUE}                 MSTTools{RESET}
{YELLOW}        Developer Utilities v{VERSION}{RESET}
""")


def status_line(ok, text):
    if ok:
        success(text)
    else:
        warning(text)


# ============================================================
# HELPERS
# ============================================================

def format_bytes(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "Unknown"

    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    for unit in units:
        if abs(value) < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} ZB"


def format_duration(seconds):
    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        return "Unknown"

    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def run(command, timeout=10):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return (result.stdout or "").strip()
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return ""
    except Exception:
        return ""


def powershell(command, timeout=10):
    if os.name != "nt":
        return ""

    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return ""

    try:
        result = subprocess.run(
            [ps, "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return (result.stdout or "").strip()
    except Exception:
        return ""


def command_exists(name):
    return shutil.which(name) is not None


def clean_value(value):
    if value is None:
        return "Unknown"
    value = str(value).strip()
    return value if value else "Unknown"


def get_cim(class_name, properties):
    if os.name != "nt":
        return {}

    props = ", ".join(properties)
    command = (
        f"Get-CimInstance Win32_{class_name} | "
        f"Select-Object {props} | ConvertTo-Json -Compress"
    )
    output = powershell(command)
    if not output:
        return {}

    try:
        data = json.loads(output)
        if isinstance(data, list):
            return data[0] if data else {}
        return data
    except Exception:
        return {}


def get_cim_all(class_name, properties):
    if os.name != "nt":
        return []

    props = ", ".join(properties)
    command = (
        f"Get-CimInstance Win32_{class_name} | "
        f"Select-Object {props} | ConvertTo-Json -Compress"
    )
    output = powershell(command)
    if not output:
        return []

    try:
        data = json.loads(output)
        return data if isinstance(data, list) else [data]
    except Exception:
        return {}


def safe_stat(path):
    try:
        return path.stat()
    except (OSError, ValueError):
        return None


def is_ignored(path):
    return any(part in IGNORED_DIRS for part in path.parts)


def project_files(root="."):
    root = Path(root)
    try:
        for path in root.rglob("*"):
            if is_ignored(path):
                continue
            try:
                if path.is_file():
                    yield path
            except OSError:
                continue
    except OSError:
        return


def read_text(path, max_bytes=5_000_000):
    try:
        stat = path.stat()
        if stat.st_size > max_bytes:
            return None
        with path.open("r", encoding="utf-8", errors="ignore") as file:
            return file.read()
    except (OSError, UnicodeError):
        return None


def count_lines(path):
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as file:
            return sum(1 for _ in file)
    except (OSError, UnicodeError):
        return 0


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    try:
        with path.open("rb") as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def relative(path, root=None):
    root = Path(root or Path.cwd())
    try:
        return str(Path(path).relative_to(root))
    except ValueError:
        return str(path)


def parse_size(value):
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmgtp]?b)?\s*", value.lower())
    if not match:
        raise ValueError("Invalid size")
    number = float(match.group(1))
    unit = match.group(2) or "b"
    multipliers = {
        "b": 1, "kb": 1024, "mb": 1024**2,
        "gb": 1024**3, "tb": 1024**4, "pb": 1024**5,
    }
    return int(number * multipliers[unit])


def safe_json_write(path, data):
    try:
        Path(path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


# ============================================================
# PROJECT CORE
# ============================================================

def collect_project_stats(root=None):
    root = Path(root or Path.cwd())
    files = list(project_files(root))
    language_files = Counter()
    language_lines = Counter()
    extensions = Counter()
    total_lines = 0
    total_bytes = 0
    largest = []

    for path in files:
        stat = safe_stat(path)
        if stat:
            total_bytes += stat.st_size
            largest.append((stat.st_size, path))

        suffix = path.suffix.lower()
        if suffix in LANGUAGES:
            language = LANGUAGES[suffix]
            language_files[language] += 1
            lines = count_lines(path)
            language_lines[language] += lines
            total_lines += lines
        elif path.name.lower() == "dockerfile":
            language_files["Dockerfile"] += 1
            lines = count_lines(path)
            language_lines["Dockerfile"] += lines
            total_lines += lines

        extensions[suffix or "[no extension]"] += 1

    largest.sort(reverse=True, key=lambda item: item[0])
    return {
        "root": str(root),
        "files": files,
        "total_files": len(files),
        "total_lines": total_lines,
        "total_bytes": total_bytes,
        "language_files": language_files,
        "language_lines": language_lines,
        "extensions": extensions,
        "largest": largest,
    }


def project_inspect():
    title("PROJECT INSPECTOR")
    data = collect_project_stats()

    if not data["files"]:
        warning("No project files found.")
        return

    label("Project", Path.cwd().name)
    label("Location", Path.cwd())
    label("Files", data["total_files"])
    label("Source lines", f"{data['total_lines']:,}")
    label("Total size", format_bytes(data["total_bytes"]))

    section("Languages")
    if data["language_files"]:
        for language, count in data["language_files"].most_common():
            lines = data["language_lines"][language]
            print(
                f"{LIGHT_BLUE}{language:<24}{RESET}"
                f" Files: {YELLOW}{count:<6}{RESET}"
                f" Lines: {WHITE}{lines:,}{RESET}"
            )
    else:
        warning("No recognized source files.")


def project_stats():
    title("PROJECT STATISTICS")
    data = collect_project_stats()

    if not data["files"]:
        warning("No files found.")
        return

    label("Total files", f"{data['total_files']:,}")
    label("Source lines", f"{data['total_lines']:,}")
    label("Project size", format_bytes(data["total_bytes"]))

    section("Language Breakdown")
    for language, lines in sorted(
        data["language_lines"].items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        count = data["language_files"][language]
        percent = (lines / data["total_lines"] * 100) if data["total_lines"] else 0
        print(
            f"{LIGHT_BLUE}{language:<22}{RESET}"
            f" Files: {YELLOW}{count:<6}{RESET}"
            f" Lines: {WHITE}{lines:<8,}{RESET}"
            f" {GRAY}{percent:5.1f}%{RESET}"
        )

    section("Largest Files")
    for size, path in data["largest"][:10]:
        print(f"{YELLOW}{relative(path):<50}{RESET} {format_bytes(size)}")


def project_health():
    title("PROJECT HEALTH")

    root = Path.cwd()
    score = 100
    checks = []

    def check(ok, good, bad, penalty=0):
        nonlocal score
        checks.append((ok, good if ok else bad))
        if not ok:
            score -= penalty

    check(
        (root / ".git").exists(),
        "Git repository detected.",
        "No Git repository detected.",
        10,
    )

    readme = any((root / name).exists() for name in ("README.md", "README.rst", "README.txt"))
    check(readme, "README detected.", "README is missing.", 8)

    license_exists = any((root / name).exists() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt"))
    check(license_exists, "License file detected.", "License file is missing.", 5)

    gitignore = (root / ".gitignore").exists()
    check(gitignore, ".gitignore detected.", ".gitignore is missing.", 5)

    tests = any(
        p.is_dir() and p.name.lower() in {"tests", "test"}
        for p in root.iterdir()
        if not is_ignored(p)
    )
    check(tests, "Test directory detected.", "No test directory detected.", 15)

    ci = any(
        (root / name).exists()
        for name in (
            ".github/workflows", ".gitlab-ci.yml", ".circleci",
            "azure-pipelines.yml", "Jenkinsfile",
        )
    )
    check(ci, "CI configuration detected.", "No CI configuration detected.", 10)

    package = any(
        (root / name).exists()
        for name in (
            "pyproject.toml", "setup.py", "package.json",
            "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
        )
    )
    check(package, "Project/package manifest detected.", "No common project manifest detected.", 7)

    env_file = (root / ".env").exists()
    check(
        not env_file,
        "No root .env file detected.",
        ".env exists in project root; keep secrets out of Git.",
        15,
    )

    score = max(0, min(100, score))

    section("Checks")
    for ok, message in checks:
        status_line(ok, message)

    section("Score")
    if score >= 90:
        success(f"Project health score: {score}/100 — excellent")
    elif score >= 75:
        success(f"Project health score: {score}/100 — good")
    elif score >= 55:
        warning(f"Project health score: {score}/100 — room for improvement")
    else:
        error(f"Project health score: {score}/100 — needs attention")


def find_large_files(limit="10MB", count=20):
    title("LARGE FILE FINDER")
    try:
        minimum = parse_size(limit)
    except ValueError:
        error("Invalid size. Examples: 500KB, 10MB, 1GB")
        return

    results = []
    for path in project_files():
        stat = safe_stat(path)
        if stat and stat.st_size >= minimum:
            results.append((stat.st_size, path))

    results.sort(reverse=True, key=lambda item: item[0])

    if not results:
        success(f"No files >= {limit} found.")
        return

    for size, path in results[:count]:
        print(f"{YELLOW}{relative(path):<55}{RESET} {format_bytes(size)}")

    info(f"Showing {min(count, len(results))} of {len(results)} matching file(s).")


def duplicate_files():
    title("DUPLICATE FILE FINDER")
    groups = defaultdict(list)

    for path in project_files():
        stat = safe_stat(path)
        if not stat or stat.st_size == 0:
            continue
        groups[stat.st_size].append(path)

    candidates = [paths for paths in groups.values() if len(paths) > 1]
    if not candidates:
        success("No duplicate-size candidates found.")
        return

    duplicates = 0
    for paths in sorted(candidates, key=lambda p: len(p), reverse=True):
        hashes = defaultdict(list)
        for path in paths:
            digest = sha256_file(path)
            if digest:
                hashes[digest].append(path)

        for digest, same in hashes.items():
            if len(same) < 2:
                continue
            duplicates += 1
            print(f"\n{MAGENTA}SHA256 {digest[:16]}...{RESET}")
            for path in same:
                print(f"  {YELLOW}{relative(path)}{RESET}")

    if duplicates:
        success(f"{duplicates} duplicate group(s) detected.")
    else:
        success("No identical files detected.")


def todo_scan():
    title("TODO / FIXME SCANNER")
    found = 0

    for path in project_files():
        text = read_text(path)
        if text is None:
            continue

        for number, line_text in enumerate(text.splitlines(), 1):
            upper = line_text.upper()
            hits = [pattern for pattern in TODO_PATTERNS if pattern in upper]
            if hits:
                print(
                    f"{YELLOW}{relative(path)}:{number}{RESET} "
                    f"{WHITE}{line_text.strip()}{RESET}"
                )
                found += 1
                if found >= 200:
                    warning("Result limit reached (200).")
                    return

    if found:
        success(f"{found} TODO-style item(s) found.")
    else:
        success("No TODO/FIXME markers found.")


def hash_file(path, algorithm="sha256"):
    title("FILE HASH")
    target = Path(path)
    if not target.is_file():
        error(f"File not found: {target}")
        return

    try:
        digest = hashlib.new(algorithm)
    except ValueError:
        error(f"Unsupported algorithm: {algorithm}")
        return

    try:
        with target.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        error(f"Could not read file: {exc}")
        return

    label("File", target)
    label("Algorithm", algorithm.upper())
    label("Digest", digest.hexdigest())


# ============================================================
# SEARCH
# ============================================================

def search_project(query, regex=False, extension=None, case_sensitive=False, max_results=200):
    title("PROJECT SEARCH")
    if not query:
        error("Search query is required.")
        return

    root = Path.cwd()
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(query, flags) if regex else None
    except re.error as exc:
        error(f"Invalid regular expression: {exc}")
        return

    found = 0
    for file in project_files(root):
        if extension:
            ext = extension.lower()
            if not ext.startswith("."):
                ext = "." + ext
            if file.suffix.lower() != ext:
                continue

        text = read_text(file)
        if text is None:
            continue

        for number, text_line in enumerate(text.splitlines(), 1):
            matched = bool(pattern.search(text_line)) if pattern else (
                query in text_line if case_sensitive
                else query.lower() in text_line.lower()
            )
            if matched:
                print(
                    f"{YELLOW}{relative(file, root)}:{number}{RESET} "
                    f"{WHITE}{text_line.strip()}{RESET}"
                )
                found += 1
                if found >= max_results:
                    warning(f"Search result limit reached ({max_results}).")
                    return

    if found:
        success(f"{found} match(es) found.")
    else:
        warning(f'No matches found for "{query}".')


# ============================================================
# GIT
# ============================================================

def git_available():
    if not command_exists("git"):
        error("Git is not installed or not available in PATH.")
        return False
    if not (Path.cwd() / ".git").exists():
        warning("Current directory is not a Git repository.")
        return False
    return True


def git_status():
    title("GIT STATUS")
    if not git_available():
        return

    output = run("git status --short")
    branch = run("git branch --show-current")
    label("Branch", branch or "Detached/Unknown")

    if output:
        print(output)
        changes = output.splitlines()
        section("Summary")
        modified = sum(1 for x in changes if x and x[0] in "MADRC")
        untracked = sum(1 for x in changes if x.startswith("??"))
        deleted = sum(1 for x in changes if "D" in x[:2])
        label("Changed entries", len(changes))
        label("Modified/staged", modified)
        label("Untracked", untracked)
        label("Deleted", deleted)
    else:
        success("Working tree clean.")


def git_log(limit=15):
    title("GIT LOG")
    if not git_available():
        return

    output = run(f"git log --oneline --decorate -{int(limit)}")
    if output:
        print(output)
    else:
        error("Git log unavailable.")


def git_info():
    title("GIT INFORMATION")
    if not git_available():
        return

    branch = run("git branch --show-current")
    remote = run("git remote get-url origin")
    commit = run("git rev-parse --short HEAD")
    full_commit = run("git rev-parse HEAD")
    commits = run("git rev-list --count HEAD")
    author = run("git log -1 --pretty=format:%an")
    subject = run("git log -1 --pretty=format:%s")
    date = run("git log -1 --pretty=format:%ad --date=iso")

    label("Branch", branch or "Detached HEAD")
    label("Remote", remote or "No origin")
    label("Current commit", commit or "Unknown")
    label("Commit SHA", full_commit or "Unknown")
    label("Total commits", commits or "Unknown")
    label("Last author", author or "Unknown")
    label("Last commit", subject or "Unknown")
    label("Last commit date", date or "Unknown")

    ahead = run("git rev-list --left-right --count @{u}...HEAD")
    if ahead:
        parts = ahead.split()
        if len(parts) == 2:
            behind, ahead_count = parts
            label("Ahead / Behind", f"{ahead_count} ahead / {behind} behind")


def git_branches():
    title("GIT BRANCHES")
    if not git_available():
        return
    output = run("git branch -vv")
    print(output or "No branches found.")


def git_remote():
    title("GIT REMOTES")
    if not git_available():
        return
    output = run("git remote -v")
    print(output or "No remotes configured.")


def git_diff(staged=False):
    title("GIT DIFF")
    if not git_available():
        return
    output = run("git diff --cached" if staged else "git diff", timeout=20)
    print(output or "No differences.")


def git_summary():
    git_status()
    git_info()


# ============================================================
# SYSTEM
# ============================================================

def system_summary():
    title("SYSTEM SUMMARY")
    label("Computer", platform.node())
    label("OS", platform.platform())
    label("Architecture", platform.machine())
    label("Processor", platform.processor() or "Unknown")
    label("Python", platform.python_version())
    label("Python executable", sys.executable)

    if os.name == "nt":
        computer = get_cim(
            "ComputerSystem",
            ["Manufacturer", "Model", "TotalPhysicalMemory"],
        )
        label("Manufacturer", clean_value(computer.get("Manufacturer")))
        label("Model", clean_value(computer.get("Model")))
        memory = computer.get("TotalPhysicalMemory")
        if memory:
            label("RAM", format_bytes(memory))

    try:
        total, used, free = shutil.disk_usage(Path.cwd())
        label("Disk free", format_bytes(free))
        label("Disk usage", f"{used / total * 100:.1f}%")
    except OSError:
        pass


def system_info():
    title("SYSTEM INFORMATION")

    section("Operating System")
    label("OS", platform.system())
    label("OS Version", platform.version())
    label("Release", platform.release())
    label("Architecture", platform.machine())
    label("Platform", platform.platform())
    label("Hostname", socket.gethostname())
    label("Username", os.environ.get("USERNAME") or os.environ.get("USER") or "Unknown")
    label("Python", platform.python_version())
    label("Python executable", sys.executable)
    label("Current directory", Path.cwd())

    if os.name != "nt":
        try:
            label("CPU count", os.cpu_count() or "Unknown")
            label("Load average", ", ".join(f"{x:.2f}" for x in os.getloadavg()))
        except (OSError, AttributeError):
            pass
        return

    section("Windows")
    os_info = get_cim(
        "OperatingSystem",
        [
            "Caption", "Version", "BuildNumber", "OSArchitecture",
            "InstallDate", "LastBootUpTime", "SerialNumber",
            "WindowsDirectory", "SystemDirectory", "RegisteredUser",
        ],
    )
    for key, field in (
        ("Edition", "Caption"), ("Build", "BuildNumber"),
        ("OS Architecture", "OSArchitecture"),
        ("Windows Directory", "WindowsDirectory"),
        ("System Directory", "SystemDirectory"),
        ("Install Date", "InstallDate"),
        ("Registered User", "RegisteredUser"),
    ):
        label(key, clean_value(os_info.get(field)))

    section("Computer")
    computer = get_cim(
        "ComputerSystem",
        [
            "Manufacturer", "Model", "SystemType", "TotalPhysicalMemory",
            "Domain", "PartOfDomain", "NumberOfLogicalProcessors",
            "NumberOfProcessors", "PCSystemType",
        ],
    )
    for key, field in (
        ("Manufacturer", "Manufacturer"), ("Model", "Model"),
        ("System Type", "SystemType"), ("Domain", "Domain"),
        ("CPU Packages", "NumberOfProcessors"),
        ("Logical CPUs", "NumberOfLogicalProcessors"),
        ("Part Of Domain", "PartOfDomain"),
    ):
        label(key, clean_value(computer.get(field)))
    if computer.get("TotalPhysicalMemory"):
        label("Installed RAM", format_bytes(computer["TotalPhysicalMemory"]))

    section("CPU")
    cpus = get_cim_all(
        "Processor",
        [
            "Name", "Manufacturer", "MaxClockSpeed", "NumberOfCores",
            "NumberOfLogicalProcessors", "SocketDesignation",
        ],
    )
    for index, cpu in enumerate(cpus, 1):
        print(f"{LIGHT_BLUE}CPU #{index}{RESET}")
        label("Name", clean_value(cpu.get("Name")))
        label("Manufacturer", clean_value(cpu.get("Manufacturer")))
        label("Cores", clean_value(cpu.get("NumberOfCores")))
        label("Threads", clean_value(cpu.get("NumberOfLogicalProcessors")))
        label("Socket", clean_value(cpu.get("SocketDesignation")))
        if cpu.get("MaxClockSpeed"):
            label("Max Clock", f"{cpu['MaxClockSpeed']} MHz")

    section("Motherboard")
    for board in get_cim_all(
        "BaseBoard", ["Manufacturer", "Product", "Version", "SerialNumber"]
    ):
        label("Manufacturer", clean_value(board.get("Manufacturer")))
        label("Product", clean_value(board.get("Product")))
        label("Version", clean_value(board.get("Version")))
        label("Serial", clean_value(board.get("SerialNumber")))

    section("BIOS")
    bios = get_cim(
        "BIOS",
        ["Manufacturer", "Name", "Version", "ReleaseDate", "SerialNumber", "SMBIOSBIOSVersion"],
    )
    for key, field in (
        ("Manufacturer", "Manufacturer"), ("Name", "Name"),
        ("Version", "Version"), ("SMBIOS Version", "SMBIOSBIOSVersion"),
        ("Release Date", "ReleaseDate"), ("Serial", "SerialNumber"),
    ):
        label(key, clean_value(bios.get(field)))

    section("GPU")
    gpus = get_cim_all(
        "VideoController",
        [
            "Name", "AdapterRAM", "DriverVersion", "VideoProcessor",
            "CurrentHorizontalResolution", "CurrentVerticalResolution",
            "CurrentRefreshRate",
        ],
    )
    for index, gpu in enumerate(gpus, 1):
        print(f"{LIGHT_BLUE}GPU #{index}{RESET}")
        label("Name", clean_value(gpu.get("Name")))
        if gpu.get("AdapterRAM"):
            label("VRAM", format_bytes(gpu["AdapterRAM"]))
        label("Driver", clean_value(gpu.get("DriverVersion")))
        label("Processor", clean_value(gpu.get("VideoProcessor")))
        width = clean_value(gpu.get("CurrentHorizontalResolution"))
        height = clean_value(gpu.get("CurrentVerticalResolution"))
        label("Resolution", f"{width}x{height}")
        label("Refresh Rate", clean_value(gpu.get("CurrentRefreshRate")))

    section("RAM Modules")
    modules = get_cim_all(
        "PhysicalMemory",
        ["Manufacturer", "PartNumber", "Capacity", "Speed", "SerialNumber", "DeviceLocator"],
    )
    for index, ram in enumerate(modules, 1):
        print(f"{LIGHT_BLUE}Module #{index}{RESET}")
        label("Manufacturer", clean_value(ram.get("Manufacturer")))
        label("Part Number", clean_value(ram.get("PartNumber")))
        if ram.get("Capacity"):
            label("Capacity", format_bytes(ram["Capacity"]))
        label("Speed", f"{clean_value(ram.get('Speed'))} MHz")
        label("Serial", clean_value(ram.get("SerialNumber")))
        label("Slot", clean_value(ram.get("DeviceLocator")))

    section("Storage")
    disks = get_cim_all(
        "DiskDrive",
        ["Model", "Manufacturer", "InterfaceType", "MediaType", "Size", "SerialNumber"],
    )
    for index, disk in enumerate(disks, 1):
        print(f"{LIGHT_BLUE}Drive #{index}{RESET}")
        label("Model", clean_value(disk.get("Model")))
        label("Manufacturer", clean_value(disk.get("Manufacturer")))
        label("Interface", clean_value(disk.get("InterfaceType")))
        label("Media Type", clean_value(disk.get("MediaType")))
        if disk.get("Size"):
            label("Size", format_bytes(disk["Size"]))
        label("Serial", clean_value(disk.get("SerialNumber")))

    section("Network Adapters")
    adapters = get_cim_all(
        "NetworkAdapterConfiguration",
        [
            "Description", "MACAddress", "IPAddress", "DefaultIPGateway",
            "DHCPEnabled", "DNSServerSearchOrder",
        ],
    )
    for adapter in adapters:
        ips = adapter.get("IPAddress")
        if not ips:
            continue
        print(f"{LIGHT_BLUE}{clean_value(adapter.get('Description'))}{RESET}")
        label("MAC", clean_value(adapter.get("MACAddress")))
        label("IP", ", ".join(ips) if isinstance(ips, list) else clean_value(ips))
        gateway = adapter.get("DefaultIPGateway")
        label("Gateway", ", ".join(gateway) if isinstance(gateway, list) else clean_value(gateway))
        dns = adapter.get("DNSServerSearchOrder")
        label("DNS", ", ".join(dns) if isinstance(dns, list) else clean_value(dns))
        label("DHCP", clean_value(adapter.get("DHCPEnabled")))

    section("Monitors")
    monitors = get_cim_all(
        "DesktopMonitor",
        ["Name", "Manufacturer", "MonitorType", "ScreenHeight", "ScreenWidth", "PNPDeviceID"],
    )
    for index, monitor in enumerate(monitors, 1):
        print(f"{LIGHT_BLUE}Monitor #{index}{RESET}")
        label("Name", clean_value(monitor.get("Name")))
        label("Manufacturer", clean_value(monitor.get("Manufacturer")))
        label("Type", clean_value(monitor.get("MonitorType")))
        label(
            "Resolution",
            f"{clean_value(monitor.get('ScreenWidth'))}x{clean_value(monitor.get('ScreenHeight'))}",
        )

    section("Firmware / Security")
    secure_boot = powershell("Confirm-SecureBootUEFI", timeout=5)
    label("Secure Boot", secure_boot or "Unavailable")

    section("Power")
    batteries = get_cim_all(
        "Battery", ["Name", "BatteryStatus", "EstimatedChargeRemaining", "EstimatedRunTime"]
    )
    if batteries:
        for battery in batteries:
            label("Battery", clean_value(battery.get("Name")))
            label("Charge", f"{clean_value(battery.get('EstimatedChargeRemaining'))}%")
            runtime = battery.get("EstimatedRunTime")
            if runtime and str(runtime) != "71582788":
                label("Estimated Runtime", f"{runtime} minutes")
    else:
        info("No battery detected.")


# ============================================================
# UPTIME / DISK
# ============================================================

def uptime():
    title("SYSTEM UPTIME")

    if os.name == "nt":
        boot = powershell(
            "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('o')",
            timeout=5,
        )
        if boot:
            try:
                boot_dt = datetime.fromisoformat(boot)
                now = datetime.now(boot_dt.tzinfo)
                seconds = max(0, int((now - boot_dt).total_seconds()))
                label("Boot Time", boot_dt.strftime("%Y-%m-%d %H:%M:%S"))
                label("Current Time", now.strftime("%Y-%m-%d %H:%M:%S"))
                label("Uptime", format_duration(seconds))
                success("Uptime information retrieved.")
                return
            except ValueError:
                pass

        boot_filetime = powershell(
            "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToFileTime()",
            timeout=5,
        )
        if boot_filetime:
            try:
                unix_seconds = int(boot_filetime) / 10_000_000 - 11644473600
                boot_dt = datetime.fromtimestamp(unix_seconds)
                now = datetime.now()
                seconds = max(0, int((now - boot_dt).total_seconds()))
                label("Boot Time", boot_dt.strftime("%Y-%m-%d %H:%M:%S"))
                label("Current Time", now.strftime("%Y-%m-%d %H:%M:%S"))
                label("Uptime", format_duration(seconds))
                success("Uptime information retrieved.")
                return
            except (ValueError, OSError):
                pass

        error("Windows uptime information could not be retrieved.")
        return

    proc = Path("/proc/uptime")
    if proc.exists():
        try:
            seconds = float(proc.read_text().split()[0])
            label("Uptime", format_duration(seconds))
            success("Uptime information retrieved.")
            return
        except (OSError, ValueError, IndexError):
            pass

    output = run("sysctl -n kern.boottime", timeout=5)
    match = re.search(r"sec = (\d+)", output or "")
    if match:
        boot_dt = datetime.fromtimestamp(int(match.group(1)))
        now = datetime.now()
        seconds = max(0, int((now - boot_dt).total_seconds()))
        label("Boot Time", boot_dt.strftime("%Y-%m-%d %H:%M:%S"))
        label("Uptime", format_duration(seconds))
        success("Uptime information retrieved.")
        return

    error("Uptime information is unavailable.")


def disk_info():
    title("DISK INFORMATION")
    if os.name == "nt":
        drives = [f"{letter}:\\" for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{letter}:\\")]
    else:
        drives = ["/"]

    for drive in drives:
        try:
            total, used, free = shutil.disk_usage(drive)
            print(f"\n{LIGHT_BLUE}{drive}{RESET}")
            label("Total", format_bytes(total))
            label("Used", format_bytes(used))
            label("Free", format_bytes(free))
            label("Usage", f"{used / total * 100:.1f}%" if total else "0%")
        except OSError:
            continue


# ============================================================
# NETWORK
# ============================================================

def network_info():
    title("NETWORK INFORMATION")
    hostname = socket.gethostname()
    label("Hostname", hostname)

    try:
        addresses = socket.getaddrinfo(hostname, None)
        ips = sorted({item[4][0] for item in addresses if item[4]})
        label("IP Addresses", ", ".join(ips))
    except socket.gaierror:
        warning("Could not determine local IP addresses.")

    section("Internet Test")
    for host, port in (("1.1.1.1", 53), ("8.8.8.8", 53)):
        start = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=3):
                latency = (time.perf_counter() - start) * 1000
            success(f"{host}:{port} reachable ({latency:.0f} ms)")
            break
        except OSError:
            continue
    else:
        error("Internet connection test failed.")

    if os.name == "nt":
        section("IP Configuration")
        output = run("ipconfig /all", timeout=10)
        if output:
            print(f"{GRAY}{output}{RESET}")


def ping_host(host, timeout=2):
    title("HOST PING")
    if not host:
        error("Host is required.")
        return

    command = ["ping", "-n" if os.name == "nt" else "-c", "1"]
    if os.name != "nt":
        command += ["-W", str(max(1, int(timeout)))]
    command.append(host)

    start = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout + 2,
        )
        elapsed = (time.perf_counter() - start) * 1000
        if result.returncode == 0:
            success(f"{host} reachable ({elapsed:.0f} ms process time)")
        else:
            error(f"{host} did not respond.")
        output = (result.stdout or "").strip()
        if output:
            print(output)
    except Exception as exc:
        error(f"Ping failed: {exc}")


def dns_lookup(host):
    title("DNS LOOKUP")
    if not host:
        error("Host is required.")
        return

    try:
        name, aliases, addresses = socket.gethostbyname_ex(host)
        label("Canonical name", name)
        label("Aliases", ", ".join(aliases) if aliases else "None")
        label("IPv4 addresses", ", ".join(addresses))
    except socket.gaierror as exc:
        error(f"DNS lookup failed: {exc}")


def http_check(url):
    title("HTTP CHECK")
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url

    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"MSTTools/{VERSION}"},
        method="GET",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            elapsed = (time.perf_counter() - start) * 1000
            label("URL", url)
            label("Status", response.status)
            label("Reason", response.reason)
            label("Content-Type", response.headers.get("Content-Type", "Unknown"))
            label("Server", response.headers.get("Server", "Unknown"))
            label("Latency", f"{elapsed:.0f} ms")
            success("HTTP request completed.")
    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        warning(f"HTTP status {exc.code} ({elapsed:.0f} ms)")
    except (urllib.error.URLError, TimeoutError) as exc:
        error(f"HTTP check failed: {exc}")


def scan_ports(host="127.0.0.1", start=None, end=None, timeout=0.15):
    title("PORT SCANNER")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        warning("MSTTools port scanning is intentionally limited to the local machine.")
        return

    if start is not None or end is not None:
        first = start if start is not None else 1
        last = end if end is not None else first
        first = max(1, int(first))
        last = min(65535, int(last))
        if last < first:
            error("Invalid port range.")
            return
        ports = range(first, last + 1)
        if last - first > 2000:
            warning("Range limited to 2000 ports for responsiveness.")
            ports = range(first, first + 2000)
    else:
        ports = COMMON_PORTS.keys()

    info(f"Scanning {host}...")
    found = []

    for port in ports:
        sock = socket.socket(socket.AF_INET6 if host == "::1" else socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            if sock.connect_ex((host, port)) == 0:
                name = COMMON_PORTS.get(port, "Unknown")
                found.append(port)
                print(
                    f"{GREEN}[OPEN]{RESET} "
                    f"{YELLOW}{port:<6}{RESET} "
                    f"{WHITE}{name}{RESET}"
                )
        except OSError:
            pass
        finally:
            sock.close()

    if found:
        success(f"{len(found)} open port(s) detected.")
    else:
        info("No open ports found in the selected range.")


# ============================================================
# PROCESS / ENVIRONMENT / DEV
# ============================================================

def process_list(filter_text=None):
    title("RUNNING PROCESSES")
    if os.name == "nt":
        command = "tasklist /FO TABLE"
    else:
        command = "ps aux"

    output = run(command, timeout=15)
    if not output:
        error("Could not retrieve process list.")
        return

    if filter_text:
        lines = output.splitlines()
        lines = [line for line in lines if filter_text.lower() in line.lower()]
        print("\n".join(lines) if lines else f'No process matched "{filter_text}".')
    else:
        print(output)


def environment_info(show_values=True):
    title("ENVIRONMENT VARIABLES")
    items = sorted(os.environ.items(), key=lambda item: item[0].lower())

    for key, value in items:
        lower = key.lower()
        if any(secret in lower for secret in SECRET_WORDS):
            value = "********"
        if not show_values:
            value = "<hidden>"
        print(f"{LIGHT_BLUE}{key:<34}{RESET}{WHITE}{value}{RESET}")


def dev_tools():
    title("DEVELOPMENT ENVIRONMENT")
    tools = [
        ("Python", "python --version"), ("PIP", "pip --version"),
        ("Git", "git --version"), ("Node.js", "node --version"),
        ("NPM", "npm --version"), ("Yarn", "yarn --version"),
        ("PNPM", "pnpm --version"), ("Docker", "docker --version"),
        ("Rust", "rustc --version"), ("Cargo", "cargo --version"),
        ("Go", "go version"), ("Java", "java -version"),
        ("PHP", "php --version"), ("Lua", "lua -v"),
        ("PowerShell", "powershell --version"),
    ]

    installed = 0
    for name, command in tools:
        output = run(command, timeout=5)
        if output:
            first = output.splitlines()[0]
            success(f"{name:<14}{first}")
            installed += 1
        else:
            print(f"{GRAY}[--] {name:<14}Not found{RESET}")

    label("Detected tools", installed)
    label("Checked tools", len(tools))


def doctor():
    title("MSTTools DOCTOR")
    root = Path.cwd()

    checks = [
        ("Python", "python --version"),
        ("Git", "git --version"),
        ("Node.js", "node --version"),
        ("npm", "npm --version"),
        ("Docker", "docker --version"),
        ("Rust", "rustc --version"),
        ("Go", "go version"),
        ("Java", "java -version"),
        ("PHP", "php --version"),
    ]

    section("Developer Tools")
    installed = 0
    for name, command in checks:
        output = run(command, timeout=5)
        if output:
            success(f"{name:<12}{output.splitlines()[0]}")
            installed += 1
        else:
            warning(f"{name:<12}Not installed / unavailable")

    section("Project")
    status_line((root / ".git").exists(), "Git repository detected." if (root / ".git").exists() else "Not a Git repository.")
    status_line((root / ".gitignore").exists(), ".gitignore detected." if (root / ".gitignore").exists() else ".gitignore is missing.")
    status_line(
        not (root / ".env").exists(),
        "No root .env file detected.",
        ".env detected in project root.",
    )

    section("Python")
    label("Version", platform.python_version())
    label("Executable", sys.executable)
    label("Prefix", sys.prefix)
    label("Virtualenv", "Yes" if sys.prefix != getattr(sys, "base_prefix", sys.prefix) else "No")
    label("pip", run("python -m pip --version", timeout=5) or "Unavailable")

    section("Disk")
    try:
        total, used, free = shutil.disk_usage(root)
        usage = used / total * 100 if total else 0
        label("Free space", format_bytes(free))
        label("Disk usage", f"{usage:.1f}%")
        if usage >= 90:
            error("Disk usage is critically high.")
        elif usage >= 80:
            warning("Disk usage is getting high.")
        else:
            success("Disk space looks healthy.")
    except OSError:
        warning("Could not check disk space.")

    section("Project Health")
    project_health()

    success(f"Detected {installed}/{len(checks)} developer tool(s).")


# ============================================================
# TREE / CLEAN / SECURITY
# ============================================================

def print_tree(path, prefix="", depth=0, max_depth=3):
    if depth > max_depth:
        return

    try:
        entries = sorted(
            [entry for entry in path.iterdir() if entry.name not in IGNORED_DIRS],
            key=lambda item: (item.is_file(), item.name.lower()),
        )
    except (PermissionError, OSError):
        return

    for index, entry in enumerate(entries):
        last = index == len(entries) - 1
        connector = "└── " if last else "├── "

        if entry.is_dir():
            print(f"{prefix}{BLUE}{connector}{entry.name}/{RESET}")
            print_tree(
                entry,
                prefix + ("    " if last else "│   "),
                depth + 1,
                max_depth,
            )
        else:
            print(f"{prefix}{LIGHT_BLUE}{connector}{entry.name}{RESET}")


def tree(max_depth=3):
    title("PROJECT TREE")
    root = Path.cwd()
    print(f"{BLUE}{root.name}/{RESET}")
    print_tree(root, max_depth=max_depth)


def clean_project(execute=False):
    title("PROJECT CLEANER")
    root = Path.cwd()
    found = []

    for path in root.rglob("*"):
        try:
            if not path.is_dir() or is_ignored(path):
                continue
            if path.name in CLEAN_TARGETS:
                if any(parent.name in CLEAN_TARGETS for parent in path.parents):
                    continue
                found.append(path)
        except OSError:
            continue

    if not found:
        success("No cleanup targets found.")
        return

    total_size = 0
    for path in found:
        size = 0
        try:
            for item in path.rglob("*"):
                stat = safe_stat(item)
                if stat and item.is_file():
                    size += stat.st_size
        except OSError:
            pass
        total_size += size
        print(f"{YELLOW}{path}{RESET} {GRAY}({format_bytes(size)}){RESET}")

    section("Summary")
    label("Folders", len(found))
    label("Estimated reclaim", format_bytes(total_size))

    if not execute:
        warning("Preview only. Nothing was deleted.")
        info("Use: mst clean --execute")
        return

    confirm = input(f"{ORANGE}Delete these folders? [y/N] {RESET}").strip().lower()
    if confirm != "y":
        warning("Cancelled. Nothing was deleted.")
        return

    deleted = 0
    for path in found:
        try:
            shutil.rmtree(path)
            deleted += 1
            success(f"Deleted: {path}")
        except OSError as exc:
            error(f"Could not delete {path}: {exc}")

    success(f"{deleted} folder(s) removed.")


def security_check():
    title("PROJECT SECURITY CHECK")
    root = Path.cwd()

    dangerous_files = {
        ".env", ".env.local", ".env.production", ".env.development",
        "id_rsa", "id_ed25519", "credentials.json", "service-account.json",
        ".npmrc", ".pypirc",
    }

    found = []
    for path in project_files(root):
        if path.name.lower() in {name.lower() for name in dangerous_files}:
            found.append(path)

    if found:
        for path in found:
            warning(f"Sensitive-looking file: {relative(path)}")
        warning("Review these files before committing or publishing.")
    else:
        success("No obvious sensitive filenames detected.")

    gitignore = root / ".gitignore"
    status_line(
        gitignore.exists(),
        ".gitignore exists.",
        ".gitignore is missing.",
    )

    if git_available():
        tracked = run("git ls-files")
        suspicious = []
        if tracked:
            for item in tracked.splitlines():
                lower = item.lower()
                if any(word in lower for word in (
                    ".env", "id_rsa", "id_ed25519", "credentials",
                    "service-account", "secret", "password",
                )):
                    suspicious.append(item)

        if suspicious:
            error("Potentially sensitive filenames are tracked by Git:")
            for item in suspicious:
                print(f"{RED}  {item}{RESET}")
        else:
            success("No obvious secret filenames are tracked by Git.")

    section("Quick Secret Pattern Scan")
    patterns = [
        re.compile(r"(?i)\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{20,}\b"),
        re.compile(r"(?i)-----BEGIN (?:RSA|EC|OPENSSH|DSA) PRIVATE KEY-----"),
    ]

    hits = 0
    for path in project_files(root):
        text = read_text(path, max_bytes=1_000_000)
        if text is None:
            continue
        for number, line_text in enumerate(text.splitlines(), 1):
            for pattern in patterns:
                if pattern.search(line_text):
                    warning(f"Possible secret pattern: {relative(path)}:{number}")
                    hits += 1
                    break
            if hits >= 50:
                warning("Secret scan result limit reached.")
                return

    if hits:
        warning(f"{hits} possible secret pattern(s) detected. Verify manually.")
    else:
        success("No obvious high-confidence secret patterns detected.")


# ============================================================
# DEPENDENCY / CONFIG ANALYSIS
# ============================================================

def dependency_info():
    title("PROJECT DEPENDENCIES")
    root = Path.cwd()
    found = []

    manifests = [
        ("Python", "requirements.txt"),
        ("Python", "requirements-dev.txt"),
        ("Python", "pyproject.toml"),
        ("Python", "Pipfile"),
        ("Python", "poetry.lock"),
        ("Node", "package.json"),
        ("Node", "package-lock.json"),
        ("Node", "yarn.lock"),
        ("Node", "pnpm-lock.yaml"),
        ("Rust", "Cargo.toml"),
        ("Rust", "Cargo.lock"),
        ("Go", "go.mod"),
        ("Go", "go.sum"),
        ("Java", "pom.xml"),
        ("Java", "build.gradle"),
        ("Java", "build.gradle.kts"),
        ("Ruby", "Gemfile"),
        ("PHP", "composer.json"),
        ("Docker", "Dockerfile"),
    ]

    for ecosystem, filename in manifests:
        path = root / filename
        if path.exists():
            found.append((ecosystem, path))

    if not found:
        warning("No recognized dependency manifests found.")
        return

    for ecosystem, path in found:
        print(f"{LIGHT_BLUE}{ecosystem:<10}{RESET}{YELLOW}{path.name}{RESET}")

    section("Python Environment")
    if (root / "requirements.txt").exists():
        lines = [
            line.strip()
            for line in (root / "requirements.txt").read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        label("requirements entries", len(lines))

    if (root / "pyproject.toml").exists():
        text = read_text(root / "pyproject.toml") or ""
        deps = re.findall(r'^\s*["\']([A-Za-z0-9_.-]+)', text, re.M)
        label("pyproject dependency-like entries", len(deps))

    section("Node Environment")
    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            deps = data.get("dependencies", {})
            dev = data.get("devDependencies", {})
            label("dependencies", len(deps))
            label("devDependencies", len(dev))
            label("package name", data.get("name", "Unknown"))
            label("package version", data.get("version", "Unknown"))
        except (OSError, json.JSONDecodeError):
            warning("Could not parse package.json.")


def project_manifest():
    title("PROJECT MANIFEST")
    root = Path.cwd()

    candidates = [
        "pyproject.toml", "setup.py", "requirements.txt", "package.json",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
        "composer.json", "Gemfile", "Dockerfile", "docker-compose.yml",
        "docker-compose.yaml", "Makefile", "README.md", "LICENSE",
    ]

    for name in candidates:
        path = root / name
        if path.exists():
            stat = safe_stat(path)
            size = format_bytes(stat.st_size) if stat else "Unknown"
            print(f"{GREEN}[FOUND]{RESET} {YELLOW}{name:<28}{RESET} {size}")

    missing = [name for name in ("README.md", ".gitignore") if not (root / name).exists()]
    if missing:
        section("Recommended")
        for name in missing:
            warning(f"Consider adding {name}.")


# ============================================================
# REPORT / SNAPSHOT / BENCHMARK
# ============================================================

def build_snapshot():
    root = Path.cwd()
    stats = collect_project_stats(root)

    snapshot = {
        "msttools_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": {
            "os": platform.system(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "hostname": socket.gethostname(),
            "python": platform.python_version(),
        },
        "project": {
            "name": root.name,
            "path": str(root),
            "files": stats["total_files"],
            "source_lines": stats["total_lines"],
            "size_bytes": stats["total_bytes"],
            "languages": dict(stats["language_lines"]),
        },
        "git": {
            "repository": (root / ".git").exists(),
            "branch": run("git branch --show-current") if (root / ".git").exists() else None,
            "commit": run("git rev-parse HEAD") if (root / ".git").exists() else None,
            "remote": run("git remote get-url origin") if (root / ".git").exists() else None,
        },
    }
    return snapshot


def report(output="msttools-report.json"):
    title("PROJECT REPORT")
    snapshot = build_snapshot()
    if safe_json_write(output, snapshot):
        label("Output", output)
        label("Project", snapshot["project"]["name"])
        label("Files", snapshot["project"]["files"])
        label("Source lines", snapshot["project"]["source_lines"])
        success("Report generated successfully.")
    else:
        error(f"Could not write report: {output}")


def benchmark():
    title("PROJECT SCAN BENCHMARK")
    root = Path.cwd()
    start = time.perf_counter()
    files = list(project_files(root))
    elapsed = time.perf_counter() - start

    total_bytes = 0
    for path in files:
        stat = safe_stat(path)
        if stat:
            total_bytes += stat.st_size

    label("Files scanned", f"{len(files):,}")
    label("Bytes indexed", format_bytes(total_bytes))
    label("Elapsed", f"{elapsed:.4f} s")
    if elapsed:
        label("Files / second", f"{len(files) / elapsed:,.0f}")
    success("Benchmark complete.")


# ============================================================
# LOCAL DEV SERVER
# ============================================================

def serve(directory=".", port=8000):
    title("LOCAL DEVELOPMENT SERVER")
    root = Path(directory).resolve()
    if not root.is_dir():
        error(f"Directory not found: {root}")
        return

    port = int(port)
    if not 1 <= port <= 65535:
        error("Port must be between 1 and 65535.")
        return

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format_string, *args):
            print(f"{GRAY}[HTTP]{RESET} {self.address_string()} - {format_string % args}")

    try:
        os.chdir(root)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), QuietHandler)
    except OSError as exc:
        error(f"Could not start server: {exc}")
        return

    info(f"Serving: {root}")
    info(f"Local URL: http://127.0.0.1:{port}")
    warning("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        warning("Server stopped.")
    finally:
        server.server_close()


# ============================================================
# INFO / DASHBOARD
# ============================================================

def about():
    title("ABOUT MSTTOOLS")
    label("Name", "MSTTools")
    label("Version", VERSION)
    label("Team", "MST TEAM")
    label("Purpose", "Developer utility CLI")
    label("Python", platform.python_version())
    label("Platform", platform.system())
    section("Modules")
    modules = [
        "System diagnostics", "Project analysis", "Git utilities",
        "Network diagnostics", "Local port scanner", "Process viewer",
        "Developer environment", "Security checks", "Project cleaner",
        "Dependency inspection", "Reports / snapshots", "Local dev server",
    ]
    for module in modules:
        print(f"{GREEN}•{RESET} {module}")


def dashboard():
    title("MSTTOOLS DASHBOARD")
    root = Path.cwd()
    stats = collect_project_stats(root)

    label("Project", root.name)
    label("MSTTools", VERSION)
    label("Files", f"{stats['total_files']:,}")
    label("Source lines", f"{stats['total_lines']:,}")
    label("Project size", format_bytes(stats["total_bytes"]))
    label("Git", "Yes" if (root / ".git").exists() else "No")
    label("README", "Yes" if (root / "README.md").exists() else "No")
    label("License", "Yes" if (root / "LICENSE").exists() else "No")
    label("Tests", "Yes" if (root / "tests").exists() else "No")

    try:
        total, used, free = shutil.disk_usage(root)
        label("Disk free", format_bytes(free))
    except OSError:
        pass

    section("Top Languages")
    for language, lines in stats["language_lines"].most_common(5):
        print(f"{LIGHT_BLUE}{language:<24}{RESET}{WHITE}{lines:,} lines{RESET}")

    if (root / ".git").exists():
        section("Git")
        label("Branch", run("git branch --show-current") or "Unknown")
        label("Commit", run("git rev-parse --short HEAD") or "Unknown")


# ============================================================
# INTERACTIVE MENU
# ============================================================

def pause():
    input(f"\n{GRAY}Press Enter to continue...{RESET}")


def interactive_menu():
    """Colorful numbered terminal interface for all MSTTools features."""
    while True:
        clear()
        show_logo()
        print(f"{GRAY}Version {VERSION}  •  {platform.system()}  •  Python {platform.python_version()}{RESET}")
        line("═", 72, LIGHT_BLUE)

        print(f"{LIGHT_BLUE}[ SYSTEM ]{RESET}")
        print(f" {BLUE}[01]{RESET} System Information        {BLUE}[02]{RESET} System Summary")
        print(f" {BLUE}[03]{RESET} System Uptime             {BLUE}[04]{RESET} Disk Information")
        print(f" {BLUE}[05]{RESET} Dashboard")
        print()

        print(f"{LIGHT_BLUE}[ PROJECT ]{RESET}")
        print(f" {BLUE}[06]{RESET} Project Inspector         {BLUE}[07]{RESET} Project Statistics")
        print(f" {BLUE}[08]{RESET} Project Health            {BLUE}[09]{RESET} Project Tree")
        print(f" {BLUE}[10]{RESET} Search Project            {BLUE}[11]{RESET} TODO / FIXME Scanner")
        print(f" {BLUE}[12]{RESET} Duplicate Finder          {BLUE}[13]{RESET} Large File Finder")
        print(f" {BLUE}[14]{RESET} Dependencies              {BLUE}[15]{RESET} Project Manifest")
        print(f" {BLUE}[16]{RESET} Project Cleaner")
        print()

        print(f"{LIGHT_BLUE}[ GIT ]{RESET}")
        print(f" {BLUE}[17]{RESET} Git Status                {BLUE}[18]{RESET} Git Log")
        print(f" {BLUE}[19]{RESET} Git Information           {BLUE}[20]{RESET} Git Branches")
        print(f" {BLUE}[21]{RESET} Git Remotes               {BLUE}[22]{RESET} Git Diff")
        print(f" {BLUE}[23]{RESET} Git Staged Diff           {BLUE}[24]{RESET} Git Summary")
        print()

        print(f"{LIGHT_BLUE}[ NETWORK ]{RESET}")
        print(f" {BLUE}[25]{RESET} Network Information       {BLUE}[26]{RESET} Ping Host")
        print(f" {BLUE}[27]{RESET} DNS Lookup                {BLUE}[28]{RESET} HTTP Check")
        print(f" {BLUE}[29]{RESET} Localhost Port Scanner")
        print()

        print(f"{LIGHT_BLUE}[ DEVELOPMENT ]{RESET}")
        print(f" {BLUE}[30]{RESET} Developer Tools           {BLUE}[31]{RESET} MSTTools Doctor")
        print(f" {BLUE}[32]{RESET} Running Processes         {BLUE}[33]{RESET} Environment Variables")
        print(f" {BLUE}[34]{RESET} Benchmark                 {BLUE}[35]{RESET} Local Development Server")
        print()

        print(f"{LIGHT_BLUE}[ SECURITY / UTILITIES ]{RESET}")
        print(f" {BLUE}[36]{RESET} Security Check            {BLUE}[37]{RESET} File Hash")
        print(f" {BLUE}[38]{RESET} Generate JSON Report      {BLUE}[39]{RESET} About MSTTools")
        print()
        print(f" {RED}[00]{RESET} Exit")
        line("═", 72, LIGHT_BLUE)

        choice = input(f"{YELLOW}Select an option > {RESET}").strip().lower()

        try:
            if choice in ("1", "01"):
                system_info()
            elif choice in ("2", "02"):
                system_summary()
            elif choice in ("3", "03"):
                uptime()
            elif choice in ("4", "04"):
                disk_info()
            elif choice in ("5", "05"):
                dashboard()

            elif choice in ("6", "06"):
                project_inspect()
            elif choice in ("7", "07"):
                project_stats()
            elif choice in ("8", "08"):
                project_health()
            elif choice in ("9", "09"):
                depth = input(f"{YELLOW}Tree depth [3] > {RESET}").strip()
                try:
                    depth = max(0, int(depth)) if depth else 3
                except ValueError:
                    depth = 3
                    warning("Invalid depth; using 3.")
                tree(depth)
            elif choice == "10":
                query = input(f"{YELLOW}Search text > {RESET}").strip()
                if query:
                    search_project(query)
                else:
                    warning("Search text cannot be empty.")
            elif choice == "11":
                todo_scan()
            elif choice == "12":
                duplicate_files()
            elif choice == "13":
                minimum = input(f"{YELLOW}Minimum size [10MB] > {RESET}").strip() or "10MB"
                find_large_files(minimum)
            elif choice == "14":
                dependency_info()
            elif choice == "15":
                project_manifest()
            elif choice == "16":
                # First preview, then optionally perform the deletion.
                clean_project(False)
                answer = input(f"{ORANGE}Run cleaner for real? [y/N] > {RESET}").strip().lower()
                if answer == "y":
                    clean_project(True)

            elif choice == "17":
                git_status()
            elif choice == "18":
                raw = input(f"{YELLOW}Commit count [15] > {RESET}").strip()
                try:
                    limit = max(1, min(100, int(raw))) if raw else 15
                except ValueError:
                    limit = 15
                    warning("Invalid count; using 15.")
                git_log(limit)
            elif choice == "19":
                git_info()
            elif choice == "20":
                git_branches()
            elif choice == "21":
                git_remote()
            elif choice == "22":
                git_diff(False)
            elif choice == "23":
                git_diff(True)
            elif choice == "24":
                git_summary()

            elif choice == "25":
                network_info()
            elif choice == "26":
                host = input(f"{YELLOW}Host [127.0.0.1] > {RESET}").strip() or "127.0.0.1"
                ping_host(host)
            elif choice == "27":
                host = input(f"{YELLOW}Hostname > {RESET}").strip()
                if host:
                    dns_lookup(host)
                else:
                    warning("Hostname cannot be empty.")
            elif choice == "28":
                url = input(f"{YELLOW}URL > {RESET}").strip()
                if url:
                    http_check(url)
                else:
                    warning("URL cannot be empty.")
            elif choice == "29":
                print(f"{GRAY}Leave both empty to scan common developer ports.{RESET}")
                first = input(f"{YELLOW}Start port [common] > {RESET}").strip()
                last = input(f"{YELLOW}End port [common] > {RESET}").strip()
                if not first and not last:
                    scan_ports()
                else:
                    try:
                        first_port = int(first or last)
                        last_port = int(last or first)
                        scan_ports("127.0.0.1", first_port, last_port)
                    except ValueError:
                        error("Ports must be numbers.")

            elif choice == "30":
                dev_tools()
            elif choice == "31":
                doctor()
            elif choice == "32":
                value = input(f"{YELLOW}Process filter [optional] > {RESET}").strip()
                process_list(value or None)
            elif choice == "33":
                environment_info()
            elif choice == "34":
                benchmark()
            elif choice == "35":
                directory = input(f"{YELLOW}Directory [.] > {RESET}").strip() or "."
                raw_port = input(f"{YELLOW}Port [8000] > {RESET}").strip() or "8000"
                try:
                    port = int(raw_port)
                    if not 1 <= port <= 65535:
                        raise ValueError
                    serve(directory, port)
                except ValueError:
                    error("Port must be between 1 and 65535.")

            elif choice == "36":
                security_check()
            elif choice == "37":
                target = input(f"{YELLOW}File path > {RESET}").strip()
                if target:
                    algorithm = input(f"{YELLOW}Algorithm [sha256] > {RESET}").strip().lower() or "sha256"
                    hash_file(target, algorithm)
                else:
                    warning("File path cannot be empty.")
            elif choice == "38":
                output = input(
                    f"{YELLOW}Report filename [msttools-report.json] > {RESET}"
                ).strip() or "msttools-report.json"
                report(output)
            elif choice == "39":
                about()

            elif choice in ("0", "00", "q", "quit", "exit"):
                clear()
                show_logo()
                print(f"{GREEN}Thanks for using MSTTools.{RESET}")
                break
            else:
                error("Invalid option. Select a number from 00 to 39.")

        except KeyboardInterrupt:
            print()
            warning("Operation cancelled.")
        except Exception as exc:
            error(f"Operation failed: {exc}")

        print()
        pause()


# ============================================================
# CLI
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(
        prog="mst",
        description="MSTTools - Developer Utility CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  mst dashboard\n"
            "  mst project health\n"
            "  mst git info\n"
            "  mst search password --extension py\n"
            "  mst ports --start 3000 --end 9000\n"
            "  mst serve --port 8000\n"
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"MSTTools {VERSION}",
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("system", help="Show detailed system information")
    sub.add_parser("summary", help="Show system summary")
    sub.add_parser("network", help="Show network information")
    sub.add_parser("dev", help="Detect installed developer tools")
    sub.add_parser("doctor", help="Run environment and project diagnostics")
    sub.add_parser("security", help="Check project for obvious security issues")
    sub.add_parser("disk", help="Show disk information")
    sub.add_parser("uptime", help="Show system uptime")
    sub.add_parser("env", help="Show environment variables")
    sub.add_parser("dashboard", help="Show a compact project dashboard")
    sub.add_parser("about", help="Show MSTTools information")
    sub.add_parser("duplicates", help="Find identical files")
    sub.add_parser("todo", help="Find TODO/FIXME markers")
    sub.add_parser("deps", help="Inspect dependency manifests")
    sub.add_parser("manifest", help="Inspect common project files")
    sub.add_parser("benchmark", help="Benchmark project file scanning")

    inspect_parser = sub.add_parser("inspect", help="Inspect current project")
    inspect_parser.set_defaults(action="inspect")

    stats_parser = sub.add_parser("stats", help="Show project statistics")
    stats_parser.set_defaults(action="stats")

    health_parser = sub.add_parser("health", help="Analyze project health")
    health_parser.set_defaults(action="health")

    project_parser = sub.add_parser("project", help="Project analysis commands")
    project_sub = project_parser.add_subparsers(dest="project_action")
    project_sub.add_parser("inspect", help="Inspect project")
    project_sub.add_parser("stats", help="Show statistics")
    project_sub.add_parser("health", help="Analyze project health")

    search_parser = sub.add_parser("search", help="Search text inside project")
    search_parser.add_argument("query")
    search_parser.add_argument("--regex", action="store_true")
    search_parser.add_argument("--extension", "-e")
    search_parser.add_argument("--case-sensitive", action="store_true")
    search_parser.add_argument("--max-results", type=int, default=200)

    tree_parser = sub.add_parser("tree", help="Show project tree")
    tree_parser.add_argument("--depth", type=int, default=3)

    clean_parser = sub.add_parser("clean", help="Find project cleanup targets")
    clean_parser.add_argument("--execute", action="store_true")

    large_parser = sub.add_parser("large", help="Find large project files")
    large_parser.add_argument("--min-size", default="10MB")
    large_parser.add_argument("--count", type=int, default=20)

    hash_parser = sub.add_parser("hash", help="Hash a file")
    hash_parser.add_argument("file")
    hash_parser.add_argument(
        "--algorithm",
        default="sha256",
        choices=sorted(hashlib.algorithms_available),
    )

    process_parser = sub.add_parser("process", help="Show running processes")
    process_parser.add_argument("--filter", "-f")

    ping_parser = sub.add_parser("ping", help="Ping a host")
    ping_parser.add_argument("host")

    dns_parser = sub.add_parser("dns", help="Resolve a hostname")
    dns_parser.add_argument("host")

    http_parser = sub.add_parser("http", help="Check an HTTP/HTTPS URL")
    http_parser.add_argument("url")

    ports_parser = sub.add_parser("ports", help="Scan localhost ports")
    ports_parser.add_argument("--start", type=int)
    ports_parser.add_argument("--end", type=int)

    serve_parser = sub.add_parser("serve", help="Serve a directory over localhost HTTP")
    serve_parser.add_argument("--directory", "-d", default=".")
    serve_parser.add_argument("--port", "-p", type=int, default=8000)

    report_parser = sub.add_parser("report", help="Write a JSON project/system report")
    report_parser.add_argument("--output", "-o", default="msttools-report.json")

    git_parser = sub.add_parser("git", help="Git utilities")
    git_parser.add_argument(
        "action",
        choices=["status", "log", "info", "branches", "remote", "diff", "staged", "summary"],
    )
    git_parser.add_argument("--limit", type=int, default=15)

    return parser


def cli():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        menu()
        return

    show_logo()

    command = args.command

    if command == "system":
        system_info()
    elif command == "summary":
        system_summary()
    elif command in {"inspect"}:
        project_inspect()
    elif command == "stats":
        project_stats()
    elif command == "health":
        project_health()
    elif command == "project":
        if args.project_action == "inspect":
            project_inspect()
        elif args.project_action == "stats":
            project_stats()
        elif args.project_action == "health":
            project_health()
        else:
            parser.parse_args(["project", "--help"])
    elif command == "network":
        network_info()
    elif command == "ports":
        scan_ports("127.0.0.1", args.start, args.end)
    elif command == "process":
        process_list(args.filter)
    elif command == "env":
        environment_info()
    elif command == "tree":
        tree(args.depth)
    elif command == "clean":
        clean_project(args.execute)
    elif command == "doctor":
        doctor()
    elif command == "security":
        security_check()
    elif command == "disk":
        disk_info()
    elif command == "uptime":
        uptime()
    elif command == "dev":
        dev_tools()
    elif command == "search":
        search_project(
            args.query,
            regex=args.regex,
            extension=args.extension,
            case_sensitive=args.case_sensitive,
            max_results=max(1, args.max_results),
        )
    elif command == "duplicates":
        duplicate_files()
    elif command == "todo":
        todo_scan()
    elif command == "large":
        find_large_files(args.min_size, max(1, args.count))
    elif command == "hash":
        hash_file(args.file, args.algorithm)
    elif command == "ping":
        ping_host(args.host)
    elif command == "dns":
        dns_lookup(args.host)
    elif command == "http":
        http_check(args.url)
    elif command == "serve":
        serve(args.directory, args.port)
    elif command == "deps":
        dependency_info()
    elif command == "manifest":
        project_manifest()
    elif command == "dashboard":
        dashboard()
    elif command == "about":
        about()
    elif command == "benchmark":
        benchmark()
    elif command == "report":
        report(args.output)
    elif command == "git":
        if args.action == "status":
            git_status()
        elif args.action == "log":
            git_log(args.limit)
        elif args.action == "info":
            git_info()
        elif args.action == "branches":
            git_branches()
        elif args.action == "remote":
            git_remote()
        elif args.action == "diff":
            git_diff(False)
        elif args.action == "staged":
            git_diff(True)
        elif args.action == "summary":
            git_summary()

def main():
    """MSTTools package/console entry point."""
    try:
        if len(sys.argv) == 1:
            interactive_menu()
        else:
            cli()
    except KeyboardInterrupt:
        print()
        warning("Operation cancelled.")
    except Exception as exc:
        print()
        error(f"Unexpected error: {exc}")


if __name__ == "__main__":
    main()
