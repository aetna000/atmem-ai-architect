"""Image-owned offline schema check; never plans/applies or executes project code."""
import json,os,shutil,subprocess,tempfile
from pathlib import Path

root=Path.cwd();files=[p for p in root.rglob('*') if p.is_file() and not p.is_symlink() and (p.name.endswith(('.tf','.tf.json')) or p.name=='.terraform.lock.hcl') and '.terraform' not in p.relative_to(root).parts]
if not files:raise SystemExit('No Terraform source was provided')
with tempfile.TemporaryDirectory(prefix='architect-schema-',dir=os.environ.get('ATMEM_TEST_DEPENDENCY_ROOT')) as folder:
 work=Path(folder)
 for source in files:
  target=work/source.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 config=work/'offline.tfrc';config.write_text('provider_installation { filesystem_mirror { path = "/opt/architect/provider-mirror" } }\n')
 environment={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(work),'TMPDIR':str(work),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1','TF_CLI_CONFIG_FILE':str(config),'AWS_EC2_METADATA_DISABLED':'true'}
 for command in [['init','-backend=false','-input=false','-no-color'],['validate','-json']]:
  result=subprocess.run(['/usr/local/bin/terraform','-chdir='+str(work),*command],env=environment,capture_output=True,text=True,timeout=120)
  print(json.dumps({'command':command[0],'exitCode':result.returncode,'output':result.stdout+result.stderr}),flush=True)
  if result.returncode:raise SystemExit(result.returncode)
