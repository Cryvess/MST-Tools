"""Portable, testable developer tools with structured results."""
import base64
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from . import __version__
from .workspace import digest, files, settings, text_file, write_json


def scan_ports(start=None, end=None):
    from .cli import COMMON_PORTS
    if start is None and end is None:
        ports = sorted(COMMON_PORTS)
    else:
        first = start if start is not None else end
        last = end if end is not None else first
        if not 1 <= first <= last <= 65535 or last - first >= 2000:
            raise ValueError('Choose an ascending range of at most 2000 ports within 1..65535')
        ports = list(range(first, last + 1))
    def probe(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return port if sock.connect_ex(('127.0.0.1', port)) == 0 else None
    with ThreadPoolExecutor(max_workers=min(64, len(ports))) as pool:
        opened = [port for port in pool.map(probe, ports) if port is not None]
    return {'host': '127.0.0.1', 'scanned': len(ports),
            'open_ports': [{'port': port, 'service_hint': COMMON_PORTS.get(port, 'Unknown')} for port in opened],
            'note': 'TCP connection checks only. Service names are conventional hints, not identification.'}


def snapshot(root, output, force=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    config = settings(root)
    entries, errors = {}, []
    for path in files(root, config['ignore'], errors):
        if path.resolve() == output:
            continue
        try:
            before = path.stat()
            sha = digest(path)
            after = path.stat()
            if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                raise OSError('File changed during snapshot; retry when writes have stopped')
            entries[path.relative_to(root).as_posix()] = {'sha256': sha, 'bytes': after.st_size}
        except OSError as exc:
            errors.append(f'{path.relative_to(root)}: {exc}')
    if errors:
        raise ValueError('Snapshot incomplete: ' + '; '.join(errors))
    data = {'schema_version': 1, 'version': __version__, 'project': root.name,
            'created_at': datetime.now(timezone.utc).isoformat(), 'files': entries}
    write_json(output, data, force)
    return {'output': str(output), 'files': len(entries),
            'bytes': sum(e['bytes'] for e in entries.values())}


def compare_snapshots(before, after):
    def load(path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(data.get('files'), dict):
            raise ValueError(f'{path}: unsupported snapshot format')
        for name, entry in data['files'].items():
            if (not isinstance(entry, dict) or not isinstance(entry.get('sha256'), str)
                    or not re.fullmatch(r'[a-f0-9]{64}', entry['sha256'])
                    or type(entry.get('bytes')) is not int or entry['bytes'] < 0):
                raise ValueError(f'{path}: invalid file entry {name}')
        return data['files']
    a, b = load(before), load(after)
    added, removed = sorted(b.keys() - a.keys()), sorted(a.keys() - b.keys())
    changed = sorted(k for k in a.keys() & b.keys() if a[k]['sha256'] != b[k]['sha256'])
    return {'added': added, 'removed': removed, 'modified': changed,
            'unchanged': len(a.keys() & b.keys()) - len(changed),
            'bytes_delta': sum(v['bytes'] for v in b.values()) - sum(v['bytes'] for v in a.values())}


def env_keys(path):
    data = {}
    for number, line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.match(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
        if not match:
            raise ValueError(f'{Path(path).name}:{number}: expected KEY=value (single-line dotenv)')
        if match[1] in data:
            raise ValueError(f'{Path(path).name}:{number}: duplicate key {match[1]}')
        value = re.split(r'\s+#', match[2], maxsplit=1)[0].strip()
        data[match[1]] = value not in ('', '""', "''")
    return data


def compare_env(example, actual):
    expected, present = env_keys(example), env_keys(actual)
    return {'missing': sorted(expected.keys() - present.keys()),
            'extra': sorted(present.keys() - expected.keys()),
            'empty': sorted(k for k in expected.keys() & present.keys() if not present[k]),
            'matched': len(expected.keys() & present.keys()),
            'note': 'Keys only. Values are never included. Single-line dotenv format.'}


def decode_jwt(token):
    parts = token.strip().split('.')
    if len(parts) != 3:
        raise ValueError('Expected a JWT with three dot-separated segments')
    def decode(part):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', part):
            raise ValueError('Invalid base64url segment')
        return json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4)).decode('utf-8'))
    try:
        header, payload = decode(parts[0]), decode(parts[1])
        if not isinstance(header, dict) or not isinstance(payload, dict):
            raise ValueError('Header and payload must be JSON objects')
    except (ValueError, UnicodeError) as exc:
        raise ValueError('JWT contains invalid JSON or base64url data') from exc
    claims = {}
    for key in ('iat', 'nbf', 'exp'):
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                claims[key] = datetime.fromtimestamp(value, timezone.utc).isoformat()
            except (OSError, OverflowError, ValueError):
                claims[key] = 'Outside supported timestamp range'
    exp = payload.get('exp')
    return {'header': header, 'payload': payload, 'timestamps': claims,
            'expired': exp < time.time() if type(exp) in (int, float) else None,
            'verified': False, 'note': 'Decoded locally. Signature NOT verified; do not use for authentication.'}


def check_http(url, timeout=8):
    if any(ord(char) < 32 for char in url):
        raise ValueError('URL contains control characters')
    if '://' not in url:
        url = 'https://' + url
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use an HTTP(S) URL without embedded credentials')
    if parsed.port == 0:
        raise ValueError('Port must be between 1 and 65535')
    request = urllib.request.Request(url, headers={'User-Agent': f'MSTTools/{__version__}'})
    start = time.perf_counter()
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        elapsed = round((time.perf_counter() - start) * 1000, 2)
        required = ['Content-Security-Policy', 'X-Content-Type-Options', 'Referrer-Policy']
        if urllib.parse.urlsplit(response.geturl()).scheme == 'https':
            required.append('Strict-Transport-Security')
        # Never include Set-Cookie or other response credentials in reports.
        return {'status': response.code, 'time_to_headers_ms': elapsed,
                'content_type': response.headers.get('Content-Type', ''),
                'server': response.headers.get('Server', ''),
                'security_headers': {k: bool(response.headers.get(k)) for k in required},
                'note': 'One GET request; timing includes connection and redirects, not full body download. '
                        'Header presence is informational, not a security verdict.'}


def check_tls(host, port=443, timeout=8):
    if not host or '/' in host or '://' in host or not 1 <= port <= 65535:
        raise ValueError('Provide a hostname and a port between 1 and 65535')
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with context.wrap_socket(raw, server_hostname=host) as connection:
            cert = connection.getpeercert()
            expires = ssl.cert_time_to_seconds(cert['notAfter'])
            return {'host': host, 'port': port, 'protocol': connection.version(),
                    'cipher': connection.cipher()[0], 'verified': True,
                    'issuer': dict(part for group in cert.get('issuer', ()) for part in group),
                    'expires': datetime.fromtimestamp(expires, timezone.utc).isoformat(),
                    'days_remaining': int((expires - time.time()) // 86400),
                    'dns_names': [v for k, v in cert.get('subjectAltName', ()) if k == 'DNS']}


def whitespace(root):
    config = settings(root)
    trailing, missing, errors = [], [], []
    for path in files(root, config['ignore'], errors):
        try:
            source = text_file(path, config['max_file_bytes'])
        except OSError as exc:
            errors.append(str(exc))
            continue
        if source is None:
            continue
        rel = path.relative_to(root).as_posix()
        for number, line in enumerate(source.splitlines(), 1):
            if line.endswith((' ', '\t')):
                trailing.append({'file': rel, 'line': number})
        if source and not source.endswith('\n'):
            missing.append(rel)
    return {'trailing_whitespace': trailing, 'missing_final_newline': missing, 'errors': errors}
