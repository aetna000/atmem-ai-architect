"""Pin reviewed native POST routes for the credential-free public control plane."""
import ast,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
files={'engineering_routes.py':'/api/engineering','emulation_routes.py':'','terraform_routes.py':'','memory_routes.py':'','voice_routes.py':'','openai_voice.py':''}
paths={'/api/architect','/api/architect/activity'};methods={path:['POST'] for path in paths};sources={}
for name,prefix in files.items():
 raw=(root/'server'/name).read_bytes();sources[name]=hashlib.sha256(raw).hexdigest()
 for node in ast.walk(ast.parse(raw)):
  if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
  for dec in node.decorator_list:
   if isinstance(dec,ast.Call) and isinstance(dec.func,ast.Attribute) and dec.func.attr in {'post','get'} and dec.args and isinstance(dec.args[0],ast.Constant):
    path=prefix+dec.args[0].value
    if name=='openai_voice.py' and path!='/api/voice/openai/status':continue
    if '{' not in path and path!='/api/engineering/orca/open':paths.add(path);methods[path]=[dec.func.attr.upper()]
(root/'hosted/workspace-routes.json').write_text(json.dumps({'sources':sources,'paths':sorted(paths),'methods':methods},indent=2)+'\n')
