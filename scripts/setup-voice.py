"""Prepare optional local dictation using an existing Whisper installation.
Downloads only the checksum-verified official tiny.en weights (~75 MiB); no API calls.
"""
import shutil, subprocess
from pathlib import Path
binary = shutil.which('whisper')
if not binary:
    raise SystemExit('Install OpenAI Whisper locally first (for example: brew install openai-whisper).')
first = Path(binary).read_text().splitlines()[0]
python = first.removeprefix('#!').strip()
if not python.startswith('/') or not Path(python).is_file():
    raise SystemExit('Whisper needs an executable Python shebang for the local voice worker.')
subprocess.run([python, '-c', "import whisper; whisper.load_model('tiny.en',device='cpu'); print('Local tiny.en speech model ready.')"],check=True)
