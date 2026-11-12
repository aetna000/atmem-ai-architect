"""Explicit local editor handoff. Never executes project files or overwrites a workspace."""
import base64
import binascii
import io
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

MAX_ZIP = 32_000_000
MAX_EXPANDED = 150_000_000


def orca_command():
    names = ['orca-ide', 'orca'] if sys.platform.startswith('linux') else ['orca']
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    candidate = Path.home()/'.local/bin/orca'
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    raise ValueError('Install Orca and enable its CLI in Settings → General → Orca CLI.')


def unpack_package(encoded, root, project):
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError('The project ZIP is invalid.') from None
    if not data or len(data) > MAX_ZIP:
        raise ValueError('Orca handoff supports ZIPs up to 32 MB. Download ZIP instead.')
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        entries = archive.infolist()
        if len(entries) > 20000 or sum(e.file_size for e in entries) > MAX_EXPANDED:
            raise ValueError('The expanded project exceeds the handoff limit.')
        seen = set()
        for entry in entries:
            name = entry.filename
            parts = PurePosixPath(name).parts
            mode = entry.external_attr >> 16
            if (not parts or name.startswith('/') or '\\' in name or '\x00' in name
                or any(part in {'.', '..'} or ':' in part or part.endswith((' ', '.')) for part in parts)
                or any(re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', part, re.I) for part in parts)
                or mode and stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}):
                raise ValueError('The ZIP contains an unsupported path or file type.')
            canonical = name.rstrip('/').casefold()
            if canonical in seen:
                raise ValueError('The ZIP contains conflicting paths.')
            seen.add(canonical)
        if not entries:
            raise ValueError('The project ZIP is empty.')
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = Path(tempfile.mkdtemp(prefix=project+'-', dir=root))
        try:
            for entry in entries:
                path = destination.joinpath(*PurePosixPath(entry.filename).parts)
                if entry.is_dir():
                    path.mkdir(parents=True, exist_ok=True)
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, path.open('xb') as target:
                    shutil.copyfileobj(source, target)
                os.chmod(path, 0o700 if (entry.external_attr >> 16) & 0o111 else 0o600)
        except Exception:
            shutil.rmtree(destination)
            raise
        return destination
    except (zipfile.BadZipFile, RuntimeError, OSError):
        raise ValueError('The project ZIP could not be prepared for Orca.') from None


def open_package(encoded, root, project):
    command = orca_command()
    destination = unpack_package(encoded, root, project)
    try:
        subprocess.run([command, 'open', '--json'], check=True, capture_output=True, timeout=30)
        subprocess.run([command, 'repo', 'add', '--path', str(destination), '--kind', 'folder', '--json'],
                       check=True, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        # Keep the prepared folder for retry/manual opening. Do not expose command output.
        return {'opened': False, 'path': str(destination), 'message': 'Orca did not open. Open this folder in Orca.'}
    return {'opened': True, 'path': str(destination)}
