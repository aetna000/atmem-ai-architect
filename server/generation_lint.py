"""Independent lint of server-generated files using operator-selected TFLint.
No plugins, cloud credentials, user config, or automatic source fixes are loaded.
"""
import json
import os
from pathlib import Path
import subprocess

def lint_generated(folder, binary):
    config=Path(folder)/'.atmem-tflint.hcl'
    config.write_text('plugin "terraform" {\n enabled = true\n preset = "recommended"\n}\n')
    env={'PATH':os.environ.get('PATH',''),'HOME':str(folder),'TMPDIR':str(folder),'CHECKPOINT_DISABLE':'1'}
    result=subprocess.run([str(binary),'--chdir='+str(folder),'--config='+str(config),'--format=json'],env=env,capture_output=True,text=True,timeout=45)
    try:
        data=json.loads(result.stdout)
    except (ValueError,TypeError):
        return {'name':'Independent Terraform lint','passed':False,'status':'failed','output':'TFLint did not return a valid JSON report.'}
    return {'name':'Independent Terraform lint','passed':result.returncode==0 and not data.get('errors') and not data.get('issues'),'status':'completed','issues':data.get('issues',[])[:100],'errors':data.get('errors',[])[:20],'output':result.stdout[-16000:]}
