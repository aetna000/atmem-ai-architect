import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

spec=importlib.util.spec_from_file_location('bounded_rag',Path(__file__).resolve().parents[2]/'src/runtime/bounded_rag.py')
rag=importlib.util.module_from_spec(spec);sys.modules[spec.name]=rag;spec.loader.exec_module(rag)

class BoundedRagTests(unittest.TestCase):
    def setUp(self):
        self.alice=rag.Principal('alice','AU');self.bob=rag.Principal('bob','US')
        self.au={'id':'au','revision':'1','title':'Australian holiday policy','text':'Sydney staff have a synthetic holiday on 12 November.','allowedSubjects':['alice'],'allowedRegions':['AU']}
        self.us={'id':'us','revision':'1','title':'SECRET US PAYROLL','text':'SECRET PAYROLL VALUE','allowedSubjects':['bob'],'allowedRegions':['US']}
    def test_acl_and_region_filter_before_scoring_or_metadata(self):
        result=rag.retrieve('holiday policy payroll',[self.au,self.us],self.alice)
        self.assertEqual([r['id'] for r in result],['au']);self.assertNotIn('SECRET',str(result))
        self.assertEqual(rag.retrieve('holiday policy',[self.au],rag.Principal('alice','US')),[])
        self.assertEqual(rag.retrieve('holiday',[{**self.au,'allowedSubjects':[]}],self.alice),[])
    def test_unknown_identity_and_oversized_collection_fail_closed(self):
        with self.assertRaises(rag.RetrievalDenied):rag.retrieve('holiday',[self.au],None)
        with self.assertRaises(ValueError):rag.retrieve('holiday',[self.au]*101,self.alice)
    def test_unsupported_question_abstains_without_model_call(self):
        repo=Mock();repo.list_bounded.return_value=[self.au];generate=Mock()
        result=rag.answer_question('quantum mechanics',self.alice,repo,generate)
        self.assertTrue(result['abstained']);generate.assert_not_called()
    def test_only_retrieved_citations_can_be_returned(self):
        evidence=rag.retrieve('holiday',[self.au,self.us],self.alice)
        with self.assertRaises(ValueError):rag.validate_answer({'answer':'Leak','citations':['us']},evidence)
        answer=rag.validate_answer({'answer':'12 November','citations':['au']},evidence)
        self.assertEqual(answer['citations'][0]['revision'],'1')
    def test_revoke_before_generation_prevents_model_access(self):
        repo=Mock();repo.list_bounded.return_value=[self.au];repo.get_current.return_value={**self.au,'allowedSubjects':[]};generate=Mock()
        with self.assertRaises(rag.RetrievalDenied):rag.answer_question('holiday',self.alice,repo,generate)
        generate.assert_not_called()
    def test_revoke_during_generation_suppresses_response(self):
        repo=Mock();repo.list_bounded.return_value=[self.au];repo.get_current.side_effect=[self.au,{**self.au,'allowedSubjects':[]}]
        generate=Mock(return_value={'answer':'12 November','citations':['au']})
        with self.assertRaises(rag.RetrievalDenied):rag.answer_question('holiday',self.alice,repo,generate)
        generate.assert_called_once()
    def test_update_or_delete_invalidates_old_evidence(self):
        for current in [None,{**self.au,'revision':'2','text':'Changed holiday'}]:
            repo=Mock();repo.list_bounded.return_value=[self.au];repo.get_current.return_value=current;generate=Mock()
            with self.assertRaises(rag.RetrievalDenied):rag.answer_question('holiday',self.alice,repo,generate)
            generate.assert_not_called()
    def test_known_question_returns_current_source_revision(self):
        repo=Mock();repo.list_bounded.return_value=[self.au,self.us];repo.get_current.return_value=self.au
        answer=rag.answer_question('holiday',self.alice,repo,lambda question,evidence:{'answer':'12 November','citations':['au']})
        self.assertFalse(answer['abstained']);self.assertEqual(repo.get_current.call_count,2)
    def test_disabled_identity_during_generation_suppresses_response(self):
        repo=Mock();repo.list_bounded.return_value=[self.au];repo.get_current.return_value=self.au
        refresh=Mock(side_effect=[self.alice,self.alice,rag.Principal('alice','US')])
        with self.assertRaises(rag.RetrievalDenied):
            rag.answer_question('holiday',self.alice,repo,lambda q,e:{'answer':'12 November','citations':['au']},refresh_principal=refresh)
