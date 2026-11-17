"""Write the generated Terraform files of a project to a directory.

    python3 scripts/terraform-emulator-render.py <workspace.json> <output directory>

Lets the apply emulator CLI (and its --trace option) run on exactly what the
product generator emits for a saved project.
"""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    project, output = Path(sys.argv[1]), Path(sys.argv[2])
    rendered = subprocess.run(['node', str(ROOT / 'scripts/terraform-render.mjs')], input=json.dumps({'project': json.loads(project.read_text()), 'environment': 'staging'}), capture_output=True, text=True, cwd=ROOT, check=True)
    for name, content in json.loads(rendered.stdout).items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise SystemExit('Unsafe generated path')
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    print(output)


if __name__ == '__main__':
    main()
