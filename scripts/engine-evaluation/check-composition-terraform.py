"""Independent local Terraform checks. Explicit offline mirror, no credential env.

All plans are terraform test mock-provider plans. Never invokes apply, migrates
state, resolves providers over the network or plans against an account.
"""
import argparse,json,os,subprocess
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--package',type=Path,required=True)
parser.add_argument('--terraform',type=Path,required=True)
parser.add_argument('--mirror',type=Path,required=True)
parser.add_argument('--evidence',type=Path,required=True)
parser.add_argument('--test',action='store_true')
args=parser.parse_args()
if args.evidence.exists():parser.error('Preserve earlier evidence; choose a new directory.')
args.evidence.mkdir(parents=True)
cli=args.evidence.resolve()/'mirror.tfrc';cli.write_text('provider_installation { filesystem_mirror { path = '+json.dumps(str(args.mirror.resolve()))+' } }\n')
env={'PATH':os.environ['PATH'],'TF_CLI_CONFIG_FILE':str(cli),'TF_IN_AUTOMATION':'1','CHECKPOINT_DISABLE':'1'}
results=[]
for command in [['init','-backend=false','-input=false','-no-color'],['validate','-no-color']]+([['test','-no-color']] if args.test else []):
    with (args.evidence/(command[0]+'.log')).open('w') as log:
        result=subprocess.run([str(args.terraform.resolve()),'-chdir='+str(args.package.resolve()),*command],env=env,stdout=log,stderr=subprocess.STDOUT)
    results.append({'command':command,'exitCode':result.returncode})
    if result.returncode:break
receipt={'package':str(args.package),'commands':results,'passed':all(r['exitCode']==0 for r in results),'boundary':'Pinned cached provider schemas and optional mock-provider configuration plans. No live account plan, application runtime or deployment evidence.'}
(args.evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
raise SystemExit(results[-1]['exitCode'])
