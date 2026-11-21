"""Separate oracle for the real UI-generated immutable line-summary package."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
OUT=ROOT/'specs/029-general-purpose-engine/evidence/20261111-validation-jobs/live-workflow'
ORACLE='''from line_summary import summarize
checks=0
def expect(lines,count,total,nonempty):
 global checks
 before=list(lines)
 assert summarize(lines)=={'count':count,'total_characters':total,'nonempty_count':nonempty}
 assert lines==before
 checks+=1
expect([],0,0,0)
expect(['','  ','a','é'],4,4,2)
expect(['x'*4096],1,4096,1)
expect(['a']*1000,1000,1000,1000)
for invalid in [None,'abc',('a',),[1],[True],[None]]:
 try:summarize(invalid)
 except TypeError:checks+=1
 else:raise AssertionError('Invalid input type accepted')
for invalid in [['x'*4097],['']*1001]:
 try:summarize(invalid)
 except ValueError:checks+=1
 else:raise AssertionError('Oversized input accepted')
original=['one','two'];summarize(original);assert original==['one','two'];checks+=1
expect(['\\t','\\n',' a '],3,5,1)
expect(['😀'],1,1,1)
print('INDEPENDENT_LINE_SUMMARY_ORACLE_PASSED',checks)
'''
manifest=json.loads((OUT/'manifest.json').read_text());archive=(OUT/'generated-package.zip').read_bytes()
assert hashlib.sha256(archive).hexdigest()==manifest['sha256']
worker=DockerValidationWorker('unix://'+str(Path.home()/'.colima/architect-qualification/docker.sock'))
spec=ValidationSpec('independent-library','sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20',('/usr/local/bin/python3','-c',ORACLE))
result=worker.run(archive,manifest['sha256'],spec)
result.update(oracleSha256=hashlib.sha256(ORACLE.encode()).hexdigest(),
    scope='15 independently authored input/output/boundary/Unicode/type/size/nonmutation checks on the actual downloaded UI-generated module; not whole-system or original 28-project acceptance.')
(OUT/'independent-oracle.py').write_text(ORACLE)
(OUT/'independent-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['status']=='passed' and 'INDEPENDENT_LINE_SUMMARY_ORACLE_PASSED 15' in result['output'],result
print('Passed 15 independent downloaded-library checks under the isolated local validator.')
