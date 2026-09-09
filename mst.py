import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


# ============================================================
# MSTTools
# MST TEAM
# Developer Utility CLI
# ============================================================

VERSION = "1.0.0"


# ============================================================
# COLORS
# ============================================================

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


# Enable ANSI colors on modern Windows terminals.
if os.name == "nt":
    os.system("")


# ============================================================
# ASCII
# ============================================================

def show_logo():
    logo = f"""
{BLUE}███╗   ███╗ ███████╗ ████████╗
████╗ ████║ ██╔════╝ ╚══██╔══╝
██╔████╔██║ ███████╗    ██║
██║╚██╔╝██║ ╚════██║    ██║
██║ ╚═╝ ██║ ███████║    ██║
╚═╝     ╚═╝ ╚══════╝    ╚═╝{RESET}

{LIGHT_BLUE}                 MSTTools{RESET}
{YELLOW}           Developer Utilities{RESET}
"""
    print(logo)


# ============================================================
# UI
# ============================================================

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def line(char="─", length=64, color=BLUE):
    print(color + char * length + RESET)


def title(text):
    print()
    line()
    print(f"{BLUE}  {text}{RESET}")
    line()


def success(text):
    print(f"{GREEN}[+] {text}{RESET}")


def warning(text):
    print(f"{ORANGE}[!] {text}{RESET}")


def error(text):
    print(f"{RED}[-] {text}{RESET}")


def info(text):
    print(f"{LIGHT_BLUE}[*] {text}{RESET}")


def label(name, value):
    print(f"{YELLOW}{name:<24}{RESET} {WHITE}{value}{RESET}")


def section(text):
    print()
    print(f"{BLUE}--- {text} ---{RESET}")


# ============================================================
# HELPERS
# ============================================================

def format_bytes(value):
    try:
        value = float(value)
    except Exception:
        return "Unknown"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]

    for unit in units:
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{value:.2f} EB"


def run(command, timeout=10):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout
        )

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        return ""

    except Exception:
        return ""


def powershell(command, timeout=10):
    if os.name != "nt":
        return ""

    ps = shutil.which("powershell") or shutil.which("pwsh")

    if not ps:
        return ""

    full_command = [
        ps,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command
    ]

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout
        )

        return result.stdout.strip()

    except Exception:
        return ""


def get_cim(class_name, properties):
    if os.name != "nt":
        return {}

    props = ", ".join(properties)

    command = (
        f"Get-CimInstance Win32_{class_name} | "
        f"Select-Object {props} | "
        f"ConvertTo-Json -Compress"
    )

    output = powershell(command)

    if not output:
        return {}

    try:
        import json

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
        f"Select-Object {props} | "
        f"ConvertTo-Json -Compress"
    )

    output = powershell(command)

    if not output:
        return []

    try:
        import json

        data = json.loads(output)

        if isinstance(data, list):
            return data

        return [data]

    except Exception:
        return []


def clean_value(value):
    if value is None:
        return "Unknown"

    value = str(value).strip()

    if not value:
        return "Unknown"

    return value


# ============================================================
# PROJECT FILES
# ============================================================

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
}


LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".jsx": "JavaScript React",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".lua": "Lua",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".json": "JSON",
    ".xml": "XML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bat": "Batch",
    ".cmd": "Batch",
    ".ps1": "PowerShell",
}


def project_files(root="."):
    root = Path(root)

    for path in root.rglob("*"):

        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        if path.is_file():
            yield path


def count_lines(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            return sum(1 for _ in file)

    except Exception:
        return 0


# ============================================================
# INSPECT
# ============================================================

def inspect_project():
    title("PROJECT INSPECTOR")

    root = Path.cwd()

    files = list(project_files(root))

    if not files:
        warning("No project files found.")
        return

    total_lines = 0
    languages = {}

    for file in files:

        suffix = file.suffix.lower()

        if suffix in LANGUAGES:
            language = LANGUAGES[suffix]

            languages[language] = languages.get(language, 0) + 1

            total_lines += count_lines(file)

    label("Project", root.name)
    label("Location", str(root))
    label("Files", len(files))
    label("Lines", total_lines)

    section("Languages")

    if languages:

        sorted_languages = sorted(
            languages.items(),
            key=lambda x: x[1],
            reverse=True
        )

        for language, amount in sorted_languages:
            print(
                f"{LIGHT_BLUE}{language:<24}{RESET}"
                f"{WHITE}{amount}{RESET}"
            )

    else:
        warning("No recognized source files.")


# ============================================================
# STATS
# ============================================================

def project_stats():
    title("PROJECT STATISTICS")

    root = Path.cwd()
    files = list(project_files(root))

    if not files:
        warning("No files found.")
        return

    language_files = {}
    language_lines = {}

    total_lines = 0

    for file in files:

        suffix = file.suffix.lower()

        if suffix not in LANGUAGES:
            continue

        language = LANGUAGES[suffix]

        lines = count_lines(file)

        language_files[language] = (
            language_files.get(language, 0) + 1
        )

        language_lines[language] = (
            language_lines.get(language, 0) + lines
        )

        total_lines += lines

    label("Total files", len(files))
    label("Source lines", total_lines)

    section("Breakdown")

    rows = sorted(
        language_files.keys(),
        key=lambda x: language_lines[x],
        reverse=True
    )

    for language in rows:

        files_count = language_files[language]
        lines = language_lines[language]

        print(
            f"{LIGHT_BLUE}{language:<22}{RESET}"
            f" Files: {YELLOW}{files_count:<6}{RESET}"
            f" Lines: {WHITE}{lines}{RESET}"
        )


# ============================================================
# SEARCH
# ============================================================

def search_project(query):
    title("PROJECT SEARCH")

    if not query:
        error("Search query is required.")
        return

    root = Path.cwd()

    found = 0

    for file in project_files(root):

        try:
            with open(
                file,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:

                for number, text in enumerate(f, 1):

                    if query.lower() in text.lower():

                        relative = file.relative_to(root)

                        print(
                            f"{YELLOW}{relative}:{number}{RESET} "
                            f"{WHITE}{text.strip()}{RESET}"
                        )

                        found += 1

                        if found >= 100:
                            warning("Search result limit reached.")
                            return

        except Exception:
            continue

    if found == 0:
        warning(f'No matches found for "{query}".')
    else:
        success(f"{found} match(es) found.")


# ============================================================
# GIT
# ============================================================

def git_status():
    title("GIT STATUS")

    output = run("git status --short")

    if output:
        print(output)
    else:
        success("Working tree clean.")


def git_log():
    title("GIT LOG")

    output = run(
        'git log --oneline --decorate -15'
    )

    if output:
        print(output)
    else:
        error("Git log unavailable.")


def git_info():
    title("GIT INFORMATION")

    if not Path(".git").exists():
        warning("Current directory is not a Git repository.")
        return

    branch = run(
        'git branch --show-current'
    )

    remote = run(
        'git remote get-url origin'
    )

    commit = run(
        'git rev-parse --short HEAD'
    )

    commits = run(
        'git rev-list --count HEAD'
    )

    label("Branch", branch or "Unknown")
    label("Remote", remote or "No origin")
    label("Current commit", commit or "Unknown")
    label("Total commits", commits or "Unknown")


# ============================================================
# SYSTEM INFO
# ============================================================

def system_info():
    title("SYSTEM INFORMATION")

    section("Operating System")

    label("OS", platform.system())
    label("OS Version", platform.version())
    label("Release", platform.release())
    label("Architecture", platform.machine())
    label("Platform", platform.platform())
    label("Hostname", socket.gethostname())
    label("Username", os.environ.get("USERNAME") or os.environ.get("USER"))
    label("Python", platform.python_version())

    if os.name == "nt":

        section("Windows")

        os_info = get_cim(
            "OperatingSystem",
            [
                "Caption",
                "Version",
                "BuildNumber",
                "OSArchitecture",
                "InstallDate",
                "LastBootUpTime",
                "SerialNumber",
                "WindowsDirectory",
                "SystemDirectory",
                "RegisteredUser",
            ]
        )

        label(
            "Edition",
            clean_value(os_info.get("Caption"))
        )

        label(
            "Build",
            clean_value(os_info.get("BuildNumber"))
        )

        label(
            "OS Architecture",
            clean_value(os_info.get("OSArchitecture"))
        )

        label(
            "Windows Directory",
            clean_value(os_info.get("WindowsDirectory"))
        )

        label(
            "System Directory",
            clean_value(os_info.get("SystemDirectory"))
        )

        label(
            "Install Date",
            clean_value(os_info.get("InstallDate"))
        )

        label(
            "Registered User",
            clean_value(os_info.get("RegisteredUser"))
        )

        section("Computer")

        computer = get_cim(
            "ComputerSystem",
            [
                "Manufacturer",
                "Model",
                "SystemType",
                "TotalPhysicalMemory",
                "Domain",
                "PartOfDomain",
                "NumberOfLogicalProcessors",
                "NumberOfProcessors",
                "PCSystemType",
            ]
        )

        label(
            "Manufacturer",
            clean_value(computer.get("Manufacturer"))
        )

        label(
            "Model",
            clean_value(computer.get("Model"))
        )

        label(
            "System Type",
            clean_value(computer.get("SystemType"))
        )

        memory = computer.get("TotalPhysicalMemory")

        if memory:
            label(
                "Installed RAM",
                format_bytes(memory)
            )

        label(
            "CPU Packages",
            clean_value(computer.get("NumberOfProcessors"))
        )

        label(
            "Logical CPUs",
            clean_value(computer.get("NumberOfLogicalProcessors"))
        )

        label(
            "Domain",
            clean_value(computer.get("Domain"))
        )

        section("CPU")

        cpus = get_cim_all(
            "Processor",
            [
                "Name",
                "Manufacturer",
                "MaxClockSpeed",
                "NumberOfCores",
                "NumberOfLogicalProcessors",
                "SocketDesignation",
                "ProcessorId",
            ]
        )

        if cpus:

            for index, cpu in enumerate(cpus, 1):

                print(
                    f"{LIGHT_BLUE}CPU #{index}{RESET}"
                )

                label(
                    "Name",
                    clean_value(cpu.get("Name"))
                )

                label(
                    "Manufacturer",
                    clean_value(cpu.get("Manufacturer"))
                )

                label(
                    "Cores",
                    clean_value(cpu.get("NumberOfCores"))
                )

                label(
                    "Threads",
                    clean_value(
                        cpu.get("NumberOfLogicalProcessors")
                    )
                )

                speed = cpu.get("MaxClockSpeed")

                if speed:
                    label(
                        "Max Clock",
                        f"{speed} MHz"
                    )

        section("Motherboard")

        boards = get_cim_all(
            "BaseBoard",
            [
                "Manufacturer",
                "Product",
                "Version",
                "SerialNumber",
            ]
        )

        for board in boards:

            label(
                "Manufacturer",
                clean_value(board.get("Manufacturer"))
            )

            label(
                "Product",
                clean_value(board.get("Product"))
            )

            label(
                "Version",
                clean_value(board.get("Version"))
            )

            label(
                "Serial Number",
                clean_value(board.get("SerialNumber"))
            )

        section("BIOS")

        bios = get_cim(
            "BIOS",
            [
                "Manufacturer",
                "Name",
                "Version",
                "ReleaseDate",
                "SerialNumber",
                "SMBIOSBIOSVersion",
            ]
        )

        label(
            "Manufacturer",
            clean_value(bios.get("Manufacturer"))
        )

        label(
            "Name",
            clean_value(bios.get("Name"))
        )

        label(
            "Version",
            clean_value(bios.get("Version"))
        )

        label(
            "SMBIOS Version",
            clean_value(bios.get("SMBIOSBIOSVersion"))
        )

        label(
            "Release Date",
            clean_value(bios.get("ReleaseDate"))
        )

        section("GPU")

        gpus = get_cim_all(
            "VideoController",
            [
                "Name",
                "AdapterRAM",
                "DriverVersion",
                "VideoProcessor",
                "CurrentHorizontalResolution",
                "CurrentVerticalResolution",
                "CurrentRefreshRate",
            ]
        )

        for index, gpu in enumerate(gpus, 1):

            print(
                f"{LIGHT_BLUE}GPU #{index}{RESET}"
            )

            label(
                "Name",
                clean_value(gpu.get("Name"))
            )

            if gpu.get("AdapterRAM"):
                label(
                    "VRAM",
                    format_bytes(gpu.get("AdapterRAM"))
                )

            label(
                "Driver",
                clean_value(gpu.get("DriverVersion"))
            )

            label(
                "Processor",
                clean_value(gpu.get("VideoProcessor"))
            )

            resolution = (
                f"{clean_value(gpu.get('CurrentHorizontalResolution'))}"
                f"x"
                f"{clean_value(gpu.get('CurrentVerticalResolution'))}"
            )

            label(
                "Resolution",
                resolution
            )

            label(
                "Refresh Rate",
                clean_value(gpu.get("CurrentRefreshRate"))
            )

        section("RAM Modules")

        ram_modules = get_cim_all(
            "PhysicalMemory",
            [
                "Manufacturer",
                "PartNumber",
                "Capacity",
                "Speed",
                "SerialNumber",
                "DeviceLocator",
            ]
        )

        for index, ram in enumerate(ram_modules, 1):

            print(
                f"{LIGHT_BLUE}Module #{index}{RESET}"
            )

            label(
                "Manufacturer",
                clean_value(ram.get("Manufacturer"))
            )

            label(
                "Part Number",
                clean_value(ram.get("PartNumber"))
            )

            if ram.get("Capacity"):
                label(
                    "Capacity",
                    format_bytes(ram.get("Capacity"))
                )

            label(
                "Speed",
                f"{clean_value(ram.get('Speed'))} MHz"
            )

            label(
                "Serial",
                clean_value(ram.get("SerialNumber"))
            )

            label(
                "Slot",
                clean_value(ram.get("DeviceLocator"))
            )

        section("Storage")

        disks = get_cim_all(
            "DiskDrive",
            [
                "Model",
                "Manufacturer",
                "InterfaceType",
                "MediaType",
                "Size",
                "SerialNumber",
            ]
        )

        for index, disk in enumerate(disks, 1):

            print(
                f"{LIGHT_BLUE}Drive #{index}{RESET}"
            )

            label(
                "Model",
                clean_value(disk.get("Model"))
            )

            label(
                "Manufacturer",
                clean_value(disk.get("Manufacturer"))
            )

            label(
                "Interface",
                clean_value(disk.get("InterfaceType"))
            )

            label(
                "Media Type",
                clean_value(disk.get("MediaType"))
            )

            if disk.get("Size"):
                label(
                    "Size",
                    format_bytes(disk.get("Size"))
                )

            label(
                "Serial",
                clean_value(disk.get("SerialNumber"))
            )

        section("Network Adapters")

        adapters = get_cim_all(
            "NetworkAdapterConfiguration",
            [
                "Description",
                "MACAddress",
                "IPAddress",
                "IPSubnet",
                "DefaultIPGateway",
                "DHCPEnabled",
                "DNSServerSearchOrder",
            ]
        )

        for adapter in adapters:

            description = clean_value(
                adapter.get("Description")
            )

            ip_addresses = adapter.get("IPAddress")

            if not ip_addresses:
                continue

            print(
                f"{LIGHT_BLUE}{description}{RESET}"
            )

            label(
                "MAC",
                clean_value(adapter.get("MACAddress"))
            )

            label(
                "IP",
                ", ".join(ip_addresses)
                if isinstance(ip_addresses, list)
                else clean_value(ip_addresses)
            )

            gateways = adapter.get(
                "DefaultIPGateway"
            )

            label(
                "Gateway",
                ", ".join(gateways)
                if isinstance(gateways, list)
                else clean_value(gateways)
            )

            dns = adapter.get(
                "DNSServerSearchOrder"
            )

            label(
                "DNS",
                ", ".join(dns)
                if isinstance(dns, list)
                else clean_value(dns)
            )

        section("Monitors")

        monitors = get_cim_all(
            "DesktopMonitor",
            [
                "Name",
                "Manufacturer",
                "MonitorType",
                "ScreenHeight",
                "ScreenWidth",
                "PNPDeviceID",
            ]
        )

        for index, monitor in enumerate(monitors, 1):

            print(
                f"{LIGHT_BLUE}Monitor #{index}{RESET}"
            )

            label(
                "Name",
                clean_value(monitor.get("Name"))
            )

            label(
                "Manufacturer",
                clean_value(monitor.get("Manufacturer"))
            )

            label(
                "Type",
                clean_value(monitor.get("MonitorType"))
            )

            resolution = (
                f"{clean_value(monitor.get('ScreenWidth'))}"
                f"x"
                f"{clean_value(monitor.get('ScreenHeight'))}"
            )

            label(
                "Resolution",
                resolution
            )

        section("BIOS / Secure Boot")

        secure_boot = powershell(
            "Confirm-SecureBootUEFI",
            timeout=5
        )

        label(
            "Secure Boot",
            secure_boot or "Unavailable"
        )

        section("Power")

        battery = get_cim_all(
            "Battery",
            [
                "Name",
                "BatteryStatus",
                "EstimatedChargeRemaining",
                "EstimatedRunTime",
            ]
        )

        if battery:

            for bat in battery:

                label(
                    "Battery",
                    clean_value(bat.get("Name"))
                )

                label(
                    "Charge",
                    f"{clean_value(bat.get('EstimatedChargeRemaining'))}%"
                )

                runtime = bat.get("EstimatedRunTime")

                if runtime and str(runtime) != "71582788":
                    label(
                        "Estimated Runtime",
                        f"{runtime} minutes"
                    )

        else:
            info("No battery detected.")

    else:

        section("Hardware")

        label("CPU", platform.processor())
        label("Machine", platform.machine())

        try:
            load = os.getloadavg()
            label(
                "Load Average",
                ", ".join(f"{x:.2f}" for x in load)
            )
        except Exception:
            pass

    section("Python Environment")

    label(
        "Python Executable",
        sys.executable
    )

    label(
        "Python Version",
        sys.version.split()[0]
    )

    label(
        "Current Directory",
        str(Path.cwd())
    )


# ============================================================
# DISK
# ============================================================

def disk_info():
    title("DISK INFORMATION")

    if os.name == "nt":

        drives = []

        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":

            path = f"{letter}:\\"

            if os.path.exists(path):
                drives.append(path)

    else:
        drives = ["/"]

    for drive in drives:

        try:
            total, used, free = shutil.disk_usage(drive)

            print(
                f"\n{LIGHT_BLUE}{drive}{RESET}"
            )

            label(
                "Total",
                format_bytes(total)
            )

            label(
                "Used",
                format_bytes(used)
            )

            label(
                "Free",
                format_bytes(free)
            )

            percentage = (
                used / total * 100
                if total
                else 0
            )

            label(
                "Usage",
                f"{percentage:.1f}%"
            )

        except Exception:
            continue


# ============================================================
# NETWORK
# ============================================================

def network_info():
    title("NETWORK INFORMATION")

    hostname = socket.gethostname()

    label(
        "Hostname",
        hostname
    )

    try:

        addresses = socket.getaddrinfo(
            hostname,
            None
        )

        ips = sorted(
            {
                item[4][0]
                for item in addresses
                if item[4]
            }
        )

        label(
            "IP Addresses",
            ", ".join(ips)
        )

    except Exception:
        warning("Could not determine IP addresses.")

    section("Internet Test")

    try:

        start = time.time()

        sock = socket.create_connection(
            ("1.1.1.1", 53),
            timeout=3
        )

        sock.close()

        latency = (
            time.time() - start
        ) * 1000

        success(
            f"Internet reachable ({latency:.0f} ms)"
        )

    except Exception:

        error(
            "Internet connection test failed."
        )

    if os.name == "nt":

        section("IP Configuration")

        output = run(
            "ipconfig /all",
            timeout=10
        )

        if output:
            print(
                f"{GRAY}{output}{RESET}"
            )


# ============================================================
# PORT SCANNER
# ============================================================

def scan_ports():

    title("LOCALHOST PORT SCANNER")

    info(
        "Scanning 127.0.0.1 for common development ports..."
    )

    ports = [
        21,
        22,
        25,
        53,
        80,
        110,
        135,
        139,
        143,
        443,
        445,
        3000,
        3306,
        5000,
        5432,
        5672,
        6379,
        8000,
        8080,
        8443,
        8888,
        27017,
    ]

    found = 0

    for port in ports:

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        sock.settimeout(0.15)

        try:

            result = sock.connect_ex(
                ("127.0.0.1", port)
            )

            if result == 0:

                print(
                    f"{GREEN}[OPEN]{RESET} "
                    f"{YELLOW}{port:<6}{RESET}"
                )

                found += 1

            else:

                print(
                    f"{GRAY}[CLOSED] {port:<6}{RESET}"
                )

        except Exception:
            pass

        finally:
            sock.close()

    print()

    if found:
        success(
            f"{found} open port(s) detected."
        )
    else:
        info("No open common development ports found.")


# ============================================================
# PROCESS LIST
# ============================================================

def process_list():

    title("RUNNING PROCESSES")

    if os.name == "nt":

        output = run(
            "tasklist /FO TABLE",
            timeout=15
        )

        if output:
            print(output)
        else:
            error("Could not retrieve process list.")

    else:

        output = run(
            "ps aux",
            timeout=15
        )

        if output:
            print(output)
        else:
            error("Could not retrieve process list.")


# ============================================================
# ENVIRONMENT
# ============================================================

def environment_info():

    title("ENVIRONMENT VARIABLES")

    items = sorted(
        os.environ.items(),
        key=lambda x: x[0].lower()
    )

    for key, value in items:

        # Hide likely secrets.
        lower = key.lower()

        if any(
            secret in lower
            for secret in [
                "password",
                "passwd",
                "secret",
                "token",
                "api_key",
                "apikey",
                "access_key",
            ]
        ):

            value = "********"

        print(
            f"{LIGHT_BLUE}{key:<32}{RESET}"
            f"{WHITE}{value}{RESET}"
        )


# ============================================================
# TREE
# ============================================================

def print_tree(
    path,
    prefix="",
    depth=0,
    max_depth=3
):

    if depth > max_depth:
        return

    try:
        entries = sorted(
            path.iterdir(),
            key=lambda p: (
                p.is_file(),
                p.name.lower()
            )
        )

    except PermissionError:
        return

    except Exception:
        return

    entries = [
        entry
        for entry in entries
        if entry.name not in IGNORED_DIRS
    ]

    for index, entry in enumerate(entries):

        last = index == len(entries) - 1

        connector = "└── " if last else "├── "

        if entry.is_dir():

            print(
                f"{prefix}{BLUE}{connector}"
                f"{entry.name}/{RESET}"
            )

            new_prefix = (
                prefix + ("    " if last else "│   ")
            )

            print_tree(
                entry,
                new_prefix,
                depth + 1,
                max_depth
            )

        else:

            print(
                f"{prefix}{LIGHT_BLUE}"
                f"{connector}{entry.name}"
                f"{RESET}"
            )


def tree():

    title("PROJECT TREE")

    print(
        f"{BLUE}{Path.cwd().name}/{RESET}"
    )

    print_tree(
        Path.cwd(),
        max_depth=3
    )


# ============================================================
# CLEAN
# ============================================================

CLEAN_TARGETS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "target",
}


def clean_project(execute=False):

    title("PROJECT CLEANER")

    root = Path.cwd()

    found = []

    for path in root.rglob("*"):

        if not path.is_dir():
            continue

        if path.name in CLEAN_TARGETS:

            if any(
                parent.name in CLEAN_TARGETS
                for parent in path.parents
            ):
                continue

            found.append(path)

    if not found:

        success("No cleanup targets found.")
        return

    print()

    for path in found:

        try:
            size = 0

            for item in path.rglob("*"):

                if item.is_file():

                    try:
                        size += item.stat().st_size
                    except Exception:
                        pass

            print(
                f"{YELLOW}{path}{RESET} "
                f"{GRAY}({format_bytes(size)}){RESET}"
            )

        except Exception:
            print(
                f"{YELLOW}{path}{RESET}"
            )

    print()

    if not execute:

        warning(
            "Preview only. Nothing was deleted."
        )

        info(
            "Use: mst clean --execute"
        )

        return

    deleted = 0

    for path in found:

        try:

            shutil.rmtree(path)

            deleted += 1

            success(
                f"Deleted: {path}"
            )

        except Exception as exc:

            error(
                f"Could not delete {path}: {exc}"
            )

    success(
        f"{deleted} folder(s) removed."
    )


# ============================================================
# DOCTOR
# ============================================================

def doctor():

    title("MSTTools DOCTOR")

    checks = [
        ("Python", "python --version"),
        ("Git", "git --version"),
        ("Node.js", "node --version"),
        ("npm", "npm --version"),
        ("Docker", "docker --version"),
        ("Rust", "rustc --version"),
        ("Go", "go version"),
    ]

    for name, command in checks:

        output = run(
            command,
            timeout=5
        )

        if output:

            first_line = output.splitlines()[0]

            success(
                f"{name:<10} {first_line}"
            )

        else:

            warning(
                f"{name:<10} Not installed / unavailable"
            )

    section("Project")

    if Path(".git").exists():
        success("Git repository detected.")
    else:
        warning("Not a Git repository.")

    if Path(".env").exists():
        warning(
            ".env file detected. Keep secrets out of Git."
        )
    else:
        success("No .env file in project root.")

    section("Disk")

    try:

        total, used, free = shutil.disk_usage(
            Path.cwd()
        )

        usage = (
            used / total * 100
            if total
            else 0
        )

        label(
            "Free space",
            format_bytes(free)
        )

        label(
            "Disk usage",
            f"{usage:.1f}%"
        )

        if usage >= 90:
            error(
                "Disk usage is critically high."
            )

        elif usage >= 80:
            warning(
                "Disk usage is getting high."
            )

        else:
            success(
                "Disk space looks healthy."
            )

    except Exception:
        warning("Could not check disk space.")


# ============================================================
# SYSTEM UPTIME
# ============================================================

def uptime():

    title("SYSTEM UPTIME")

    if os.name == "nt":

        # Windows'un son açılış zamanını doğrudan
        # PowerShell üzerinden alıyoruz.
        boot_time = powershell(
            "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('o')",
            timeout=5
        )

        if boot_time:

            try:
                from datetime import datetime

                # Örnek:
                # 2026-09-09T08:42:15.1234567+03:00
                boot_dt = datetime.fromisoformat(
                    boot_time
                )

                now = datetime.now(
                    boot_dt.tzinfo
                )

                delta = now - boot_dt

                total_seconds = int(
                    delta.total_seconds()
                )

                if total_seconds < 0:
                    total_seconds = 0

                days = total_seconds // 86400
                hours = (
                    total_seconds % 86400
                ) // 3600

                minutes = (
                    total_seconds % 3600
                ) // 60

                seconds = (
                    total_seconds % 60
                )

                label(
                    "Boot Time",
                    boot_dt.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                label(
                    "Current Time",
                    now.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                label(
                    "Uptime",
                    f"{days}d "
                    f"{hours}h "
                    f"{minutes}m "
                    f"{seconds}s"
                )

                success(
                    "Uptime information retrieved."
                )

                return

            except Exception:
                pass

        # ----------------------------------------------------
        # Windows fallback
        # ----------------------------------------------------

        boot_ms = powershell(
            "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToFileTime()",
            timeout=5
        )

        if boot_ms:

            try:
                boot_filetime = int(
                    boot_ms
                )

                # Windows FILETIME:
                # 100-nanosecond intervals since
                # 1601-01-01 UTC.
                unix_seconds = (
                    boot_filetime / 10_000_000
                    - 11644473600
                )

                boot_dt = datetime.fromtimestamp(
                    unix_seconds
                )

                now = datetime.now()

                delta = now - boot_dt

                total_seconds = int(
                    delta.total_seconds()
                )

                if total_seconds < 0:
                    total_seconds = 0

                days = total_seconds // 86400
                hours = (
                    total_seconds % 86400
                ) // 3600

                minutes = (
                    total_seconds % 3600
                ) // 60

                seconds = (
                    total_seconds % 60
                )

                label(
                    "Boot Time",
                    boot_dt.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                label(
                    "Current Time",
                    now.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                label(
                    "Uptime",
                    f"{days}d "
                    f"{hours}h "
                    f"{minutes}m "
                    f"{seconds}s"
                )

                success(
                    "Uptime information retrieved."
                )

                return

            except Exception:
                pass

        error(
            "Windows uptime information could not be retrieved."
        )

        return

    # ========================================================
    # Linux / Unix
    # ========================================================

    try:

        proc_uptime = Path(
            "/proc/uptime"
        )

        if proc_uptime.exists():

            with open(
                proc_uptime,
                "r",
                encoding="utf-8"
            ) as file:

                seconds = float(
                    file.read().split()[0]
                )

            total_seconds = int(seconds)

            days = total_seconds // 86400

            hours = (
                total_seconds % 86400
            ) // 3600

            minutes = (
                total_seconds % 3600
            ) // 60

            secs = (
                total_seconds % 60
            )

            label(
                "Uptime",
                f"{days}d "
                f"{hours}h "
                f"{minutes}m "
                f"{secs}s"
            )

            success(
                "Uptime information retrieved."
            )

            return

    except Exception:
        pass

    # macOS fallback
    try:

        output = run(
            "sysctl -n kern.boottime",
            timeout=5
        )

        if output:

            import re
            from datetime import datetime

            match = re.search(
                r"sec = (\d+)",
                output
            )

            if match:

                boot_timestamp = int(
                    match.group(1)
                )

                boot_dt = datetime.fromtimestamp(
                    boot_timestamp
                )

                now = datetime.now()

                delta = now - boot_dt

                total_seconds = int(
                    delta.total_seconds()
                )

                days = total_seconds // 86400

                hours = (
                    total_seconds % 86400
                ) // 3600

                minutes = (
                    total_seconds % 3600
                ) // 60

                secs = (
                    total_seconds % 60
                )

                label(
                    "Boot Time",
                    boot_dt.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                label(
                    "Uptime",
                    f"{days}d "
                    f"{hours}h "
                    f"{minutes}m "
                    f"{secs}s"
                )

                success(
                    "Uptime information retrieved."
                )

                return

    except Exception:
        pass

    error(
        "Uptime information is unavailable."
    )


# ============================================================
# DEV TOOLS
# ============================================================

def dev_tools():

    title("DEVELOPMENT ENVIRONMENT")

    tools = [
        ("Python", "python --version"),
        ("PIP", "pip --version"),
        ("Git", "git --version"),
        ("Node", "node --version"),
        ("NPM", "npm --version"),
        ("Yarn", "yarn --version"),
        ("PNPM", "pnpm --version"),
        ("Docker", "docker --version"),
        ("Rust", "rustc --version"),
        ("Cargo", "cargo --version"),
        ("Go", "go version"),
        ("Java", "java -version"),
        ("PHP", "php --version"),
        ("Lua", "lua -v"),
        ("PowerShell", "powershell --version"),
    ]

    for name, command in tools:

        output = run(
            command,
            timeout=5
        )

        if output:

            first = output.splitlines()[0]

            success(
                f"{name:<14}{first}"
            )

        else:

            print(
                f"{GRAY}[--] {name:<14}Not found{RESET}"
            )


# ============================================================
# PROJECT SECURITY CHECK
# ============================================================

def security_check():

    title("PROJECT SECURITY CHECK")

    root = Path.cwd()

    dangerous_files = [
        ".env",
        ".env.local",
        ".env.production",
        "id_rsa",
        "id_rsa.pub",
        ".npmrc",
    ]

    found = []

    for name in dangerous_files:

        path = root / name

        if path.exists():

            found.append(path)

    if found:

        for path in found:

            warning(
                f"Sensitive-looking file: {path}"
            )

        warning(
            "Make sure these files are not committed to Git."
        )

    else:

        success(
            "No obvious sensitive files detected."
        )

    gitignore = root / ".gitignore"

    if gitignore.exists():

        success(
            ".gitignore exists."
        )

    else:

        warning(
            ".gitignore is missing."
        )

    if (root / ".git").exists():

        tracked = run(
            "git ls-files"
        )

        suspicious = []

        if tracked:

            for line_text in tracked.splitlines():

                name = line_text.lower()

                if any(
                    secret in name
                    for secret in [
                        ".env",
                        "id_rsa",
                        "credentials",
                        "secret",
                        "password",
                    ]
                ):

                    suspicious.append(
                        line_text
                    )

        if suspicious:

            error(
                "Potentially sensitive files are tracked:"
            )

            for item in suspicious:
                print(
                    f"{RED}  {item}{RESET}"
                )

        else:

            success(
                "No obvious secret filenames tracked by Git."
            )


# ============================================================
# SYSTEM SUMMARY
# ============================================================

def system_summary():

    title("SYSTEM SUMMARY")

    label("Computer", platform.node())
    label("OS", platform.platform())
    label("Architecture", platform.machine())
    label("CPU", platform.processor())
    label("Python", platform.python_version())

    if os.name == "nt":

        computer = get_cim(
            "ComputerSystem",
            [
                "Manufacturer",
                "Model",
                "TotalPhysicalMemory",
            ]
        )

        label(
            "Manufacturer",
            clean_value(
                computer.get("Manufacturer")
            )
        )

        label(
            "Model",
            clean_value(
                computer.get("Model")
            )
        )

        memory = computer.get(
            "TotalPhysicalMemory"
        )

        if memory:

            label(
                "RAM",
                format_bytes(memory)
            )

    try:

        total, used, free = shutil.disk_usage(
            Path.cwd()
        )

        label(
            "Disk Free",
            format_bytes(free)
        )

    except Exception:
        pass


# ============================================================
# MENU
# ============================================================

def menu():

    while True:

        clear()
        show_logo()

        print(
            f"{BLUE}[1]{RESET} "
            f"{WHITE}System Information{RESET}"
        )

        print(
            f"{BLUE}[2]{RESET} "
            f"{WHITE}System Summary{RESET}"
        )

        print(
            f"{BLUE}[3]{RESET} "
            f"{WHITE}Project Inspect{RESET}"
        )

        print(
            f"{BLUE}[4]{RESET} "
            f"{WHITE}Project Stats{RESET}"
        )

        print(
            f"{BLUE}[5]{RESET} "
            f"{WHITE}Git Tools{RESET}"
        )

        print(
            f"{BLUE}[6]{RESET} "
            f"{WHITE}Network Information{RESET}"
        )

        print(
            f"{BLUE}[7]{RESET} "
            f"{WHITE}Port Scanner{RESET}"
        )

        print(
            f"{BLUE}[8]{RESET} "
            f"{WHITE}Running Processes{RESET}"
        )

        print(
            f"{BLUE}[9]{RESET} "
            f"{WHITE}Development Tools{RESET}"
        )

        print(
            f"{BLUE}[10]{RESET} "
            f"{WHITE}Project Tree{RESET}"
        )

        print(
            f"{BLUE}[11]{RESET} "
            f"{WHITE}Project Search{RESET}"
        )

        print(
            f"{BLUE}[12]{RESET} "
            f"{WHITE}Cleaner{RESET}"
        )

        print(
            f"{BLUE}[13]{RESET} "
            f"{WHITE}Doctor{RESET}"
        )

        print(
            f"{BLUE}[14]{RESET} "
            f"{WHITE}Security Check{RESET}"
        )

        print(
            f"{BLUE}[15]{RESET} "
            f"{WHITE}Disk Information{RESET}"
        )

        print(
            f"{BLUE}[16]{RESET} "
            f"{WHITE}Environment Variables{RESET}"
        )

        print(
            f"{BLUE}[17]{RESET} "
            f"{WHITE}Uptime{RESET}"
        )

        print(
            f"{RED}[0]{RESET} "
            f"{WHITE}Exit{RESET}"
        )

        line()

        choice = input(
            f"{YELLOW}MSTTools > {RESET}"
        ).strip()

        if choice == "1":
            system_info()

        elif choice == "2":
            system_summary()

        elif choice == "3":
            inspect_project()

        elif choice == "4":
            project_stats()

        elif choice == "5":
            git_status()
            git_log()
            git_info()

        elif choice == "6":
            network_info()

        elif choice == "7":
            scan_ports()

        elif choice == "8":
            process_list()

        elif choice == "9":
            dev_tools()

        elif choice == "10":
            tree()

        elif choice == "11":

            query = input(
                f"{YELLOW}Search > {RESET}"
            )

            search_project(query)

        elif choice == "12":
            clean_project(False)

        elif choice == "13":
            doctor()

        elif choice == "14":
            security_check()

        elif choice == "15":
            disk_info()

        elif choice == "16":
            environment_info()

        elif choice == "17":
            uptime()

        elif choice == "0":
            clear()
            show_logo()
            print(
                f"{GREEN}Thanks for using MSTTools.{RESET}"
            )
            break

        else:
            error("Invalid option.")

        input(
            f"\n{GRAY}Press Enter to continue...{RESET}"
        )


# ============================================================
# CLI
# ============================================================

def cli():

    parser = argparse.ArgumentParser(
        prog="mst",
        description="MSTTools - Developer Utility CLI"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"MSTTools {VERSION}"
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    subparsers.add_parser(
        "system",
        help="Show detailed system information"
    )

    subparsers.add_parser(
        "summary",
        help="Show system summary"
    )

    subparsers.add_parser(
        "inspect",
        help="Inspect current project"
    )

    subparsers.add_parser(
        "stats",
        help="Show project statistics"
    )

    subparsers.add_parser(
        "network",
        help="Show network information"
    )

    subparsers.add_parser(
        "ports",
        help="Scan localhost development ports"
    )

    subparsers.add_parser(
        "process",
        help="Show running processes"
    )

    subparsers.add_parser(
        "env",
        help="Show environment variables"
    )

    subparsers.add_parser(
        "tree",
        help="Show project tree"
    )

    subparsers.add_parser(
        "doctor",
        help="Check development environment"
    )

    subparsers.add_parser(
        "security",
        help="Check project for obvious security issues"
    )

    subparsers.add_parser(
        "disk",
        help="Show disk information"
    )

    subparsers.add_parser(
        "uptime",
        help="Show system uptime"
    )

    subparsers.add_parser(
        "dev",
        help="Detect installed developer tools"
    )

    search_parser = subparsers.add_parser(
        "search",
        help="Search text inside project"
    )

    search_parser.add_argument(
        "query",
        help="Text to search for"
    )

    clean_parser = subparsers.add_parser(
        "clean",
        help="Find project cleanup targets"
    )

    clean_parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete detected targets"
    )

    git_parser = subparsers.add_parser(
        "git",
        help="Git utilities"
    )

    git_parser.add_argument(
        "action",
        choices=[
            "status",
            "log",
            "info",
        ]
    )

    args = parser.parse_args()

    if not args.command:

        menu()
        return

    show_logo()

    if args.command == "system":
        system_info()

    elif args.command == "summary":
        system_summary()

    elif args.command == "inspect":
        inspect_project()

    elif args.command == "stats":
        project_stats()

    elif args.command == "network":
        network_info()

    elif args.command == "ports":
        scan_ports()

    elif args.command == "process":
        process_list()

    elif args.command == "env":
        environment_info()

    elif args.command == "tree":
        tree()

    elif args.command == "doctor":
        doctor()

    elif args.command == "security":
        security_check()

    elif args.command == "disk":
        disk_info()

    elif args.command == "uptime":
        uptime()

    elif args.command == "dev":
        dev_tools()

    elif args.command == "search":
        search_project(args.query)

    elif args.command == "clean":
        clean_project(args.execute)

    elif args.command == "git":

        if args.action == "status":
            git_status()

        elif args.action == "log":
            git_log()

        elif args.action == "info":
            git_info()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        cli()

    except KeyboardInterrupt:

        print()
        warning("Operation cancelled.")

    except Exception as exc:

        print()
        error(f"Unexpected error: {exc}")