#!/usr/bin/env python3
"""Run the local native-engineering preview with explicit operator configuration.

No tool/image installation, account lookup or deployment. The browser uses the
backend session API; local CLI execution is only this development worker transport.
"""
import argparse,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--home',type=Path,required=True,help='App control/data directory, never the model workspace')
parser.add_argument('--port',type=int,default=5274)
parser.add_argument('--sidecar-port',type=int,default=8866)
parser.add_argument('--tools',type=Path,help='Operator JSON with readRoots and tools; no credentials')
parser.add_argument('--validator-endpoint',default=os.getenv('ATMEM_ARCHITECT_ENGINEERING_VALIDATOR_ENDPOINT'),help='Explicit owned local Docker Unix endpoint; no context discovery')
parser.add_argument('--validators',type=Path,help='Operator registered local validator definitions')
parser.add_argument('--isolation-profiles',type=Path,help='Operator named reviewed isolation-profile paths/digests')
parser.add_argument('--vite-cache',type=Path)
args=parser.parse_args()
if not 1024<=args.port<=65535 or not 1024<=args.sidecar_port<=65535 or args.port==args.sidecar_port:parser.error('Choose distinct unprivileged local ports')
def read(path,default):return json.loads(path.read_text())if path else default
tools=read(args.tools,{'readRoots':[],'tools':{}})
if not isinstance(tools,dict)or set(tools)!={'readRoots','tools'}:parser.error('Tool registration requires exactly readRoots and tools')
settings={'ENABLE_ENGINEERING':'1','PORT':str(args.port),'SIDECAR_PORT':str(args.sidecar_port),'HOME':str(args.home.resolve()),'ENGINEERING_TOOL_ROOTS':json.dumps(tools['readRoots']),'ENGINEERING_TOOLCHAIN':json.dumps(tools['tools']),'ENGINEERING_VALIDATOR_ENDPOINT':args.validator_endpoint or '', 'ENGINEERING_VALIDATORS':json.dumps(read(args.validators,[])),'ENGINEERING_ISOLATION_PROFILES':json.dumps(read(args.isolation_profiles,{})),'VITE_CACHE_DIR':str((args.vite_cache or args.home/'vite-cache').resolve())}
# Endpoint is an explicit operator argument/environment setting, never inferred
# from the current Docker context. No Docker access is given to native commands.
env=dict(os.environ)
if args.validator_endpoint is None:env['ATFORMA_ENGINEERING_VALIDATOR_ENDPOINT']=''
env.update({'ATMEM_ARCHITECT_'+key:value for key,value in settings.items()})
os.chdir(ROOT);os.execvpe('node',['node',str(ROOT/'scripts/local.mjs')],env)
