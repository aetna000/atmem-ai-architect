"""Current product settings, with legacy installation compatibility."""
import os
from pathlib import Path

def setting(name):
    return os.getenv('ATMEM_ARCHITECT_' + name) or os.getenv('ATFORMA_' + name)

def home():
    configured = setting('HOME')
    if configured:
        return Path(configured)
    legacy = Path.home() / '.atforma'
    # Preserve scoped memory identities and project history in existing installations.
    return legacy if legacy.exists() else Path.home() / '.atmem-ai-architect'
