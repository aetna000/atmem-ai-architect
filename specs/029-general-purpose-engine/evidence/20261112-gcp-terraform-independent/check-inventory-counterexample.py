"""Additional API credential grant must be rejected even if known worker grant remains correct."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
ROOT=Path(__file__).resolve().parents[4];bulk=ROOT/'.local/external-artifacts/native-amd64-runtime/v1';baseline=bulk/'terraform-independent-v5';out=bulk/'terraform-counterexample-additional-api-token-v1';out.mkdir();cfg=out/'configuration';shutil.copytree(baseline/'configuration',cfg)
original=ROOT/'.local/external-artifacts/native-gcp-water/v1/native-run/unpacked/infra/main.tf';source=original.read_bytes()
extra='''
resource "google_secret_manager_secret_iam_member" "additional_api_token" {
 secret_id = google_secret_manager_secret.destination_token.id
 role = "roles/secretmanager.secretAccessor"
 member = "serviceAccount:${google_service_account.runtime["api"].email}"
}
'''
(cfg/'main.tf').write_bytes(source+extra.encode())
env={'PATH':os.environ['PATH'],'TF_CLI_CONFIG_FILE':str(baseline/'mirror.tfrc'),'TF_DATA_DIR':str(out/'terraform-data'),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1'}
with(out/'init.log').open('wb')as target:r=subprocess.run([str(ROOT/'.venv/bin/terraform'),'-chdir='+str(cfg),'init','-backend=false','-input=false','-lockfile=readonly','-no-color'],env=env,stdout=target,stderr=subprocess.STDOUT)
assert r.returncode==0
with(out/'test.jsonl').open('wb')as target:r=subprocess.run([str(ROOT/'.venv/bin/terraform'),'-chdir='+str(cfg),'test','-test-directory=plan-review','-json','-verbose','-no-color'],env=env,stdout=target,stderr=subprocess.STDOUT)
assert r.returncode==0,'Known-resource assertions should remain true in this counterexample'
events=[json.loads(line)for line in(out/'test.jsonl').read_text().splitlines()];plan=next(event['test_plan']for event in events if event.get('type')=='test_plan')
values={item['address']:item['change']['after']for item in plan['resource_changes']if item['mode']=='managed'};token=values['google_secret_manager_secret.destination_token']['id'];grants=[value for address,value in values.items()if address.startswith('google_secret_manager_secret_iam_member.')and value['secret_id']==token]
api='serviceAccount:'+values['google_service_account.runtime["api"]']['email'];worker='serviceAccount:'+values['google_service_account.runtime["worker"]']['email'];assert len(grants)==2 and {v['member']for v in grants}=={api,worker}
assert not(len(grants)==1 and grants[0]['member']==worker),'The independent inventory predicate must reject the extra grant'
assert original.read_bytes()==source
receipt={'passed':True,'counterexample':'additional API token grant with original worker grant intact','knownResourceAssertionsPass':True,'completeInventoryRejects':True,'tokenGrantCount':len(grants),'originalSourceUnchanged':True,'originalMainSha256':hashlib.sha256(source).hexdigest(),'mutatedMainSha256':hashlib.sha256((cfg/'main.tf').read_bytes()).hexdigest(),'rawPlanSha256':hashlib.sha256((out/'test.jsonl').read_bytes()).hexdigest(),'cloudOperations':False,'scope':'Independent inventory oracle qualification; not a source fix or client-package change'}
(out/'receipt-v1.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
