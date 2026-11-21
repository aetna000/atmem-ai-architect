"""Native protocol/skill-discovery probe; no inference or engineering turn."""
import asyncio,hashlib,json,pathlib,sys,tempfile,subprocess
ROOT=pathlib.Path.cwd();sys.path.insert(0,str(ROOT))
from server.codex_app_server import CodexAppServer
from server.skills import registry
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-codex-session-foundation'
async def main():
 skill=next(x for x in registry() if x['id']=='composition')
 if not skill['integrity']:raise ValueError('Reviewed skill integrity failed')
 with tempfile.TemporaryDirectory(prefix='atmem-codex-protocol-') as folder:
  base=pathlib.Path(folder);target=base/'.agents/skills/atmem-composition/SKILL.md';target.parent.mkdir(parents=True);target.write_text(skill['instructions'])
  client=CodexAppServer(base)
  try:
   initialized=await client.start()
   models,skills=await asyncio.gather(client.request('model/list',{'limit':100}),client.request('skills/list',{'cwds':[str(base)],'forceReload':True}))
   rows=[r for entry in skills.get('data',[]) for r in entry.get('skills',[]) if pathlib.Path(r.get('path','')).resolve()==target.resolve()]
   if len(rows)!=1:raise ValueError('Native Codex did not discover the reviewed workspace skill')
   result={'passed':True,'boundary':'Native installed app-server handshake, model catalogue and workspace skill discovery only; no model turn, Terraform generation, sandbox isolation or product integration qualification','cliVersion':subprocess.check_output(['codex','--version'],text=True).strip(),'initialized':bool(initialized),'modelCount':len(models.get('data',[])),'skillDiscovered':rows[0].get('name'),'skillSha256':hashlib.sha256(target.read_bytes()).hexdigest(),'expectedSkillSha256':skill['digest'],'cloudOperations':False,'inferenceTurns':0}
   (OUT/'native-protocol-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
  finally:await client.close()
asyncio.run(main())
