"""Exercise actual OpenSpec file dependencies with real reviewer results, no agents/cloud."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from atmem_review.engine import review_plan

ROOT=Path(__file__).resolve().parents[1]

def status(directory):
    command=['npm','exec','--yes','--package=@fission-ai/openspec@2.1.0','--','openspec','status','--change','review-demo','--json']
    value=subprocess.run(command,cwd=directory,capture_output=True,text=True,timeout=60,check=True)
    result=json.loads(value.stdout)
    return {a['id']:a['status'] for a in result['artifacts']}


def main():
    with tempfile.TemporaryDirectory(prefix='atmem-openspec-test-') as directory:
        base=Path(directory);schema=base/'openspec/schemas/atmem-reviewed'
        shutil.copytree(ROOT/'openspec/schemas/atmem-reviewed',schema)
        (base/'openspec/config.yaml').write_text('schema: atmem-reviewed\n')
        change=base/'openspec/changes/review-demo';(change/'specs/reviewer').mkdir(parents=True)
        (change/'.openspec.yaml').write_text('schema: atmem-reviewed\ncreated: 2026-11-17\n')
        for path,text in [('proposal.md','# Review supplied infrastructure\n'),('design.md','# Design\nUse the explicitly supplied Terraform JSON.\n'),
                          ('specs/reviewer/spec.md','# Policy review\n## ADDED Requirements\n### Requirement: Review precedes tasks\nThe system SHALL require review.\n#### Scenario: No review\n- **WHEN** review is missing\n- **THEN** tasks remain blocked\n')]:
            (change/path).write_text(text)
        payload=json.loads((ROOT/'examples/review-input.sample.json').read_text())
        payload['workflow']='openspec';payload['artifacts']=[{'kind':kind,'path':p,'content':(change/p).read_text()} for kind,p in
            [('proposal','proposal.md'),('design','design.md'),('spec','specs/reviewer/spec.md')]]
        before=status(base);assert before['tasks']=='blocked' and before['review']=='ready'
        failed=review_plan(payload);assert failed['verdict']=='fail'
        (change/'review.blocked.md').write_text('VERDICT: FAIL\n```json\n'+json.dumps(failed)+'\n```\n')
        blocked=status(base);assert blocked['tasks']=='blocked'
        corrected=json.loads((ROOT/'demo/generated/after.input.json').read_text())
        payload['terraform_plan']=corrected['terraform_plan']
        warned=review_plan(payload);assert warned['verdict']=='warn'
        (change/'review.md').write_text('VERDICT: WARN\n```json\n'+json.dumps(warned)+'\n```\n')
        accepted=status(base);assert accepted['tasks']=='ready'
        # The agent wrapper's documented re-review operation invalidates an old
        # current report; the underlying graph itself only checks file existence.
        (change/'review.md').rename(change/'review.previous.md')
        (change/'review.blocked.md').write_text('VERDICT: FAIL\n```json\n'+json.dumps(failed)+'\n```\n')
        reblocked=status(base);assert reblocked['tasks']=='blocked'
        assert not (change/'tasks.md').exists()
    print(json.dumps({'status':'passed','openspecVersion':'2.1.0','before':before,'afterFail':blocked,'afterWarn':accepted,'afterFailedRereview':reblocked,
                      'evidenceLevel':'real_cli_artifact_dependency_with_real_local_review_results','agentPromptObedienceTested':False,'cloudCalls':0,'livePricing':False}))


if __name__=='__main__':main()
