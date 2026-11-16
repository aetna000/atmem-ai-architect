"""Install the isolated Terraform apply emulator runtime.

Creates .local/terraform-emulator-runtime from a hash-locked closure. It never
alters the server environment, installs Terraform providers or contacts a cloud
account. Terraform 1.7+ itself must already be installed.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'server/terraform-emulator-requirements.lock'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', default=sys.executable, help='Python 3.11+ interpreter for the runtime')
    parser.add_argument('--runtime', default=str(ROOT / '.local/terraform-emulator-runtime'))
    options = parser.parse_args()
    interpreter = shutil.which(options.python) or options.python
    version = subprocess.check_output([interpreter, '-I', '-c', 'import sys;print("%d.%d" % sys.version_info[:2])'], text=True).strip()
    if tuple(map(int, version.split('.'))) < (3, 11):
        raise SystemExit('The emulator runtime requires Python 3.11 or newer.')
    runtime = Path(options.runtime)
    subprocess.run([interpreter, '-I', '-m', 'venv', str(runtime)], check=True)
    python = runtime / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    subprocess.run([str(python), '-I', '-m', 'pip', '--isolated', 'install', '--disable-pip-version-check', '--only-binary=:all:', '--require-hashes', '-r', str(LOCK)], check=True)
    subprocess.run([str(python), '-I', '-m', 'pip', 'check'], check=True)
    subprocess.run([str(python), '-I', '-c', 'import moto, flask, flask_cors, boto3; assert moto.__version__ == "5.2.5"'], check=True)
    print('Terraform emulator runtime ready:', python)


if __name__ == '__main__':
    main()
