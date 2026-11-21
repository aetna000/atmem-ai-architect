"""Read-only native history inspection for the owned synthetic live workflow.

Records hashes and narrow tool facts only; no raw native handles, tool contents,
credentials or private command/environment values are copied into evidence.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-validation-jobs/live-workflow'
receipt=json.loads((OUT/'receipt.json').read_text())
config=json.loads((ROOT/'.local/engineering-preview/operator-toolchain.json').read_text())
with sqlite3.connect(ROOT/'.local/engineering-preview/engineering/control.sqlite') as db:
    db.row_factory=sqlite3.Row
    row=dict(db.execute('''SELECT s.* FROM engineering_sessions s WHERE id=? AND tenant='local-owner' AND project=?''',
        (receipt['sessionId'],receipt['projectId'])).fetchone())
    workspace=db.execute('SELECT path FROM engineering_workspaces WHERE id=? AND tenant=? AND project=?',
        (row['workspace'],row['tenant'],row['project'])).fetchone()[0]
    runs=db.execute('SELECT count(*) FROM engineering_runs WHERE session=?',(row['id'],)).fetchone()[0]
assert row['state']=='idle' and row['last_status']=='completed' and runs==1
skill=(ROOT/'agent-skills/specialists/composition/SKILL.md').read_text()


async def main():
    client=CodexWorkerClient(workspace,read_roots=config['readRoots'])
    try:
        await client.start();await client.verify_worker_tools()
        history=await client.request('thread/read',{'threadId':row['handle'],'includeTurns':True})
        turns=history['thread']['turns'];owned=[turn for turn in turns if turn['id']==row['turn']]
        assert len(owned)==1 and owned[0]['status']=='completed'
        facts=[];kinds={}
        for item in owned[0]['items']:
            kind=item.get('type','unknown');kinds[kind]=kinds.get(kind,0)+1
            if kind=='commandExecution':
                command=item.get('command','');output=item.get('aggregatedOutput','') or ''
                if 'SKILL.md' in command:
                    facts.append({'itemType':kind,'exitCode':item.get('exitCode'),'status':item.get('status'),
                        'commandSha256':hashlib.sha256(command.encode()).hexdigest(),
                        'outputSha256':hashlib.sha256(output.encode()).hexdigest(),
                        'fullPinnedSkillInOutput':skill.strip() in output})
        result={'acceptedNativeRuns':runs,'model':row['model'],'effort':row['effort'],
            'reviewedSkillSha256':hashlib.sha256(skill.encode()).hexdigest(),'skillReadFacts':facts,'itemKinds':kinds,
            'inferenceTurnsForInspection':0,'cloudOperations':False,
            'boundary':'Read-only history of the owned completed synthetic native turn. Successful command output must contain the entire pinned reviewed skill; hashes and counts only are retained. Invocation is not architecture quality.'}
        (OUT/'native-skill-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
        assert any(fact['exitCode']==0 and fact['fullPinnedSkillInOutput'] for fact in facts),result
    finally:await client.close()

asyncio.run(main())
