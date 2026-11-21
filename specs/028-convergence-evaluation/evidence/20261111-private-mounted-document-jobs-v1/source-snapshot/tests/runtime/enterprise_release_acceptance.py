"""Delayed answer policy with scripted native source and model boundaries."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from enterprise_knowledge_acceptance import Source
from enterprise_knowledge import EnterpriseKnowledge
from enterprise_sources import SourceDenied,SourceChanged,SourceUnavailable


class DelayedRelease(unittest.TestCase):
    def setUp(self):
        self.source=Source();self.events=[];self.company=[]
        def generate(payload,schema,instruction):
            row=json.loads(payload)['articles'][0]
            return json.dumps({'answer':'Retention is ninety days.','abstained':False,'citations':[{'id':row['id'],'quote':'Approved retention is ninety days.'}]})
        self.engine=EnterpriseKnowledge([self.source],generate,lambda raw,mime:raw.decode(),audit=self.events.append,authorize=self.company.append)
        self.receipt=self.engine.answer_receipt('What is retention?','alice')

    def test_delayed_result_rechecks_selection_versions_company_and_audit(self):
        before=len(self.company);result=self.engine.release(self.receipt,'alice')
        self.assertEqual(result,self.receipt['answer']);self.assertEqual(len(self.company)-before,2)
        self.assertEqual(len(self.source.searches),2);self.assertEqual(self.source.gates,3)
        self.assertEqual(self.events[-1]['event'],'knowledge.release')
        self.assertNotIn('ninety',json.dumps(self.events))

    def test_revoked_document_denies_saved_answer(self):
        self.source.revoke_at=3
        with self.assertRaises(SourceDenied):self.engine.release(self.receipt,'alice')

    def test_changed_selection_invalidates_answer_even_if_old_document_exists(self):
        self.source.search=lambda *args,**kwargs:['new-document']
        with self.assertRaises(SourceChanged):self.engine.release(self.receipt,'alice')

    def test_empty_source_outage_never_releases_saved_answer(self):
        empty=Source('sharepoint:other');empty.search=lambda *args,**kwargs:[]
        self.engine.sources=(self.source,empty);receipt=self.engine.answer_receipt('What is retention?','alice')
        def fail(*args,**kwargs):raise SourceUnavailable('source_request_failed')
        empty.search=fail
        with self.assertRaises(SourceUnavailable):self.engine.release(receipt,'alice')

    def test_company_revocation_after_source_validation_denies_release(self):
        checks=[]
        def authorize(subject):
            checks.append(subject)
            if len(checks)==2:raise SourceDenied('company_membership_required')
        self.engine.authorize=authorize
        with self.assertRaises(SourceDenied):self.engine.release(self.receipt,'alice')

    def test_saved_receipt_cannot_select_another_source_or_drop_version_evidence(self):
        for change in ['source','missing','duplicate','format']:
            value=copy.deepcopy(self.receipt)
            if change=='source':value['selections'][0]['source']='unconfigured'
            elif change=='missing':value['documents']=[]
            elif change=='duplicate':value['documents'].append(value['documents'][0])
            else:value['format']='model-invented'
            with self.subTest(change=change),self.assertRaises(SourceUnavailable):self.engine.release(value,'alice')


if __name__=='__main__':unittest.main(verbosity=2)
