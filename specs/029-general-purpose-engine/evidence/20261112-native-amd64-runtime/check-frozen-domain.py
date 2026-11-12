"""Independent pre-inference policy cases against unchanged captured code.

This covers pure domain validation, not HTTP, role, persistence or whole-system acceptance.
"""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
cases_path=ROOT/'specs/029-general-purpose-engine/evidence/20261112-native-gcp-water/requirements-cases-v1.json'
code=r'''
import json,sys,unittest
sys.path.insert(0,'/work/source/application')
from sample_domain import source,process,result
cases=json.loads(sys.argv[1]);assert cases['frozenBeforeInference'] is True
class FrozenPolicy(unittest.TestCase):
 def test_valid_sources_and_exact_expected_output(self):
  for index,case in enumerate(cases['validSourceCases']):
   with self.subTest(case=index):
    value=case['source'];expected=case['expectedResult']
    self.assertEqual(source(value),value);self.assertEqual(process(value),expected)
    self.assertEqual(result(value,expected),expected)
 def test_invalid_sources_are_rejected(self):
  for index,case in enumerate(cases['invalidSourceCases']):
   with self.subTest(case=index),self.assertRaises((ValueError,UnicodeError)):source(case['source'])
 def test_review_note_bounds_and_derived_immutability(self):
  for index,case in enumerate(cases['validSourceCases']):
   original=case['source'];expected=case['expectedResult']
   for note in cases['reviewCases']['validNotes']:
    with self.subTest(case=index,kind='valid note'):
     approved={**expected,'reviewNote':note};self.assertEqual(result(original,approved),approved)
   for note in cases['reviewCases']['invalidNotes']:
    with self.subTest(case=index,kind='invalid note'),self.assertRaises((ValueError,UnicodeError)):result(original,{**expected,'reviewNote':note})
   for field,value in [('readingNgPerL',expected['readingNgPerL']+1),('dutyPriority','normal' if expected['dutyPriority']=='urgent' else 'urgent')]:
    with self.subTest(case=index,kind=field),self.assertRaises(ValueError):result(original,{**expected,field:value})
print(json.dumps({'oracle':'frozen pre-inference policy cases','validSourceCases':len(cases['validSourceCases']),'invalidSourceCases':len(cases['invalidSourceCases']),'reviewNoteCasesPerSource':len(cases['reviewCases']['validNotes'])+len(cases['reviewCases']['invalidNotes']),'derivedMutationCasesPerSource':2,'httpOrRoleAcceptance':False}))
unittest.main(argv=['frozen-policy'],verbosity=2)
'''
content=(ROOT/'.local/external-artifacts/native-gcp-water/v1/native-run/artifact.zip').read_bytes();sha=hashlib.sha256(content).hexdigest();assert sha=='69bdacf7d6813bfdd977b007abe7c94d8c3308cb2e09f9fd09c6cb39cf61031d'
spec=ValidationSpec('frozen-policy-check','sha256:bafc5723ac59b025d42337e4c965e6d7b89a07da3d18b49a9384cfa70274f8e2',('/usr/local/bin/python3','-I','-c',code,cases_path.read_text()),platform='linux/amd64',timeout_seconds=30)
worker=DockerValidationWorker('unix:///Users/javadtaghia/.avm/c/amd64/validator.sock')
result=worker.run(content,sha,spec);result['oracleCasesSha256']=hashlib.sha256(cases_path.read_bytes()).hexdigest();result['oracleSourceSha256']=hashlib.sha256(code.encode()).hexdigest()
with (ROOT/'.local/external-artifacts/native-amd64-runtime/v1/frozen-domain-v1.json').open('x') as target:target.write(json.dumps(result,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items() if key not in {'command','output'}}));assert result['status']=='passed'
