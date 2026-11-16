"""Fixed container entry point. Input is an immutable Terraform artifact, never a command."""
import json,os,sys,threading
from pathlib import Path
sys.path.insert(0,'/opt/architect')
from server.terraform_emulator import emulate_directory
# PID 1 exiting terminates all processes even if the outside controller disappears.
watchdog=threading.Timer(1450,lambda:os._exit(124));watchdog.daemon=True;watchdog.start()
try:
    os.environ['ATMEM_EMULATOR_WHEELHOUSE']='/opt/architect/emulator-wheels'
    def progress(event):print('ATMEM_EMULATION_EVENT:'+json.dumps(event,separators=(',',':')),flush=True)
    report=emulate_directory(Path.cwd(),'/usr/local/bin/terraform',provider_cache='/opt/architect/provider-mirror',progress=progress)
    print('ATMEM_EMULATION_REPORT:'+json.dumps(report,separators=(',',':')),flush=True)
    raise SystemExit(0 if report['status']=='passed' else 1)
finally:watchdog.cancel()
