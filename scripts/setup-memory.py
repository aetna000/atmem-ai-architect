"""Install the tested AtMem runtime separately from model SDK dependencies."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import venv

root = Path(__file__).resolve().parent.parent
folder = root / '.memory-venv'
python = folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
locked = str(root / 'server/memory-requirements.lock')
uv = shutil.which('uv')

if uv:
    if not python.exists():
        subprocess.run([uv, 'venv', '--python', sys.executable, str(folder)], check=True)
    subprocess.run([uv, 'pip', 'install', '--python', str(python), '--require-hashes', '-r', locked], check=True)
else:
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(folder)
    elif subprocess.run([str(python), '-m', 'pip', '--version'], capture_output=True).returncode:
        subprocess.run([str(python), '-m', 'ensurepip', '--default-pip'], check=True)
    subprocess.run([str(python), '-m', 'pip', 'install', '--require-hashes', '-r', locked], check=True)

print('AtMem runtime installed. AtMem AI Architect uses its own scoped store; existing installations retain their data directory.')
