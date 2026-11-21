"""Independent evaluator invariants using synthetic receipts, not engine outputs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('independent_engine_assessor',ROOT/'scripts/engine-evaluation/assess.py')
assessor=importlib.util.module_from_spec(spec);spec.loader.exec_module(assessor)

class EngineEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.contract=json.loads(assessor.CONTRACT.read_text());self.rules=self.contract['requiredChecks']
        self.case={'case':'aws-synthetic','provider':'aws','difficulty':'simple'}
        (self.root/'artifact.zip').write_bytes(b'synthetic artifact, not a real package')
        (self.root/'evidence.txt').write_text('synthetic independent receipt fixture')
        artifact={'path':'artifact.zip','sha256':assessor.sha(self.root/'artifact.zip')}
        self.record={'case':self.case['case'],'provider':'aws','artifact':artifact,'checks':[
            {'id':r['id'],'status':'passed','level':r['levels'][0],
             'verifier':{'id':'synthetic-independent-verifier','sha256':'a'*64},
             'evidence':{'path':'evidence.txt','sha256':assessor.sha(self.root/'evidence.txt'),'artifactSha256':artifact['sha256']}}
            for r in self.rules]}
    def tearDown(self):self.temp.cleanup()
    def evaluate(self):
        (self.root/'acceptance.json').write_text(json.dumps(self.record))
        return assessor.assess_case(self.root,self.case,self.rules)
    def test_complete_correctly_bound_receipts_pass_the_aggregator_only(self):
        self.assertTrue(self.evaluate()['qualified'])
    def test_missing_skipped_and_claimed_mock_runtime_evidence_never_qualify(self):
        for mutation in [lambda c:c.update(status='skipped'),lambda c:c.update(level='provider-mock'),lambda c:c.update(evidence={}),lambda c:c.update(verifier={})]:
            with self.subTest(mutation=mutation):
                original=copy.deepcopy(self.record)
                mutation(next(c for c in self.record['checks'] if c['id']=='journey'))
                self.assertFalse(self.evaluate()['qualified']);self.record=original
    def test_modified_artifact_invalidates_every_old_pass(self):
        (self.root/'artifact.zip').write_bytes(b'changed')
        self.assertFalse(any(c['passed'] for c in self.evaluate()['checks']))
    def test_evidence_cannot_bind_a_different_artifact(self):
        self.record['checks'][0]['evidence']['artifactSha256']='b'*64
        self.assertFalse(self.evaluate()['qualified'])
    def test_external_files_and_symlinks_are_rejected(self):
        (self.root/'alias').symlink_to(self.root/'evidence.txt')
        for name in ['alias','../outside','/etc/hosts']:
            self.record['checks'][0]['evidence']['path']=name
            self.assertFalse(self.evaluate()['qualified'])
    def test_duplicate_checks_and_wrong_provider_are_invalid(self):
        self.record['checks'].append(copy.deepcopy(self.record['checks'][0]))
        with self.assertRaises(ValueError):self.evaluate()
        self.record['checks'].pop();self.record['provider']='gcp'
        with self.assertRaises(ValueError):self.evaluate()
    def test_empty_matrix_reports_all_original_cases_missing_in_every_stratum(self):
        result=assessor.assess(self.root)
        self.assertEqual(result['expectedCases'],28);self.assertEqual(result['qualifiedCases'],0)
        self.assertEqual(len(result['strata']),12);self.assertFalse(result['accepted'])
        self.assertTrue(all(s['noncriticalPassed']==0 and s['noncriticalRequired']>0 for s in result['strata']))
