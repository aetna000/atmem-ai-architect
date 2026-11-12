"""Test-only mutations prove independent assertions detect missing safeguards.

Never edits the captured package or its accepted receiving configuration.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
ROOT=Path(__file__).resolve().parents[4];bulk=ROOT/'.local/external-artifacts/native-amd64-runtime/v1';baseline=bulk/'terraform-independent-v5';original=ROOT/'.local/external-artifacts/native-gcp-water/v1/native-run/unpacked/infra';source=(original/'main.tf').read_bytes();receipts=[]
def mutate(text,kind):
 if kind=='iap-disabled':
  old='iap_enabled          = true';assert text.count(old)==1;return text.replace(old,'iap_enabled          = false')
 start=text.index('resource "google_secret_manager_secret_iam_member" "worker_token"');end=text.index('resource "google_cloud_run_v2_service"',start);section=text[start:end];old='google_service_account.runtime["worker"].email';assert section.count(old)==1
 return text[:start]+section.replace(old,'google_service_account.runtime["api"].email')+text[end:]
for kind,message in [('iap-disabled','Native IAP service identity owns invoker grant'),('api-token-grant','Destination token access belongs to worker')]:
 out=bulk/('terraform-counterexample-'+kind+'-v1');out.mkdir();cfg=out/'configuration';shutil.copytree(baseline/'configuration',cfg)
 (cfg/'main.tf').write_text(mutate(source.decode(),kind))
 env={'PATH':os.environ['PATH'],'TF_CLI_CONFIG_FILE':str(baseline/'mirror.tfrc'),'TF_DATA_DIR':str(out/'terraform-data'),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1'}
 with (out/'init.log').open('wb')as log:r=subprocess.run([str(ROOT/'.venv/bin/terraform'),'-chdir='+str(cfg),'init','-backend=false','-input=false','-lockfile=readonly','-no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
 assert r.returncode==0
 with (out/'test.jsonl').open('wb')as log:r=subprocess.run([str(ROOT/'.venv/bin/terraform'),'-chdir='+str(cfg),'test','-test-directory=plan-review','-json','-no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
 events=[json.loads(line)for line in(out/'test.jsonl').read_text().splitlines()];diagnostics=[event.get('diagnostic',{})for event in events if event.get('type')=='diagnostic']
 assert r.returncode==1 and any(d.get('summary')=='Test assertion failed'and message in d.get('detail','')for d in diagnostics),diagnostics
 assert (original/'main.tf').read_bytes()==source
 assert all(p.read_bytes()==(original/p.name).read_bytes()for p in cfg.glob('*.tf')if p.name!='main.tf')
 receipt={'counterexample':kind,'passed':True,'deliberatelyInvalidFixtureRejected':True,'expectedAssertion':message,'testExitCode':r.returncode,'originalSourceUnchanged':True,'mutationMainSha256':hashlib.sha256((cfg/'main.tf').read_bytes()).hexdigest(),'originalMainSha256':hashlib.sha256(source).hexdigest(),'logSha256':hashlib.sha256((out/'test.jsonl').read_bytes()).hexdigest(),'cloudOperations':False}
 (out/'receipt-v1.json').write_text(json.dumps(receipt,indent=2)+'\n');receipts.append(receipt)
(bulk/'terraform-counterexamples-v1.json').write_text(json.dumps({'passed':True,'counterexamples':receipts,'scope':'Independent oracle qualification only, not a client export fix'},indent=2)+'\n');print(json.dumps(receipts))
