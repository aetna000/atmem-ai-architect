"""Serve the compiled UI and the authenticated loopback API from one process."""
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from .app import app

frontend=Path(__file__).resolve().parents[1]/'dist'
if not (frontend/'index.html').is_file():
    raise RuntimeError('The installed package has no compiled UI. Reinstall the complete Architect package.')
app.mount('/',StaticFiles(directory=frontend,html=True),name='architect-ui')
