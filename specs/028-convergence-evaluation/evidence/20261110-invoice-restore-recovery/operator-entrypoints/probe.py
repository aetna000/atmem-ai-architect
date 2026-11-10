import json,os,subprocess,sys,tempfile
from pathlib import Path
with tempfile.TemporaryDirectory()as folder:
 p=Path(folder)/"deployment.json";p.write_text(json.dumps({"provider":sys.argv[1],"deploymentId":"11111111-1111-4111-8111-111111111111","accountId":"11111111-1111-4111-8111-111111111111","namespace":"invoice","bindings":{},"tenantId":None}));p.chmod(0o600)
 r=subprocess.run([sys.executable,"-I","/app/invoice_operator.py","initialize","--connection-file","/not-used-in-preview","--deployment-file",str(p)],capture_output=True,text=True,timeout=10)
 assert r.returncode==0,(r.returncode,r.stderr)
 assert json.loads(r.stdout)["willWrite"]is False
 print(json.dumps({"provider":sys.argv[1],"actualIsolatedOperatorCli":"passed","databaseConnection":"none; preview only"}))
