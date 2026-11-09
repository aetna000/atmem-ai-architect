import unittest
from server.engineering_knowledge import records,publish,context
class FakeMemory:
    def __init__(self,enabled=True):self.values=[];self.active=enabled
    def enabled(self,p):return self.active
    def enqueue(self,*args,**kwargs):self.values.append((args,kwargs))
class EngineeringKnowledgeTests(unittest.TestCase):
    def test_curated_sources_cover_all_clouds_with_pins_and_evidence_boundaries(self):
        rows=records();self.assertEqual({r['provider'] for r in rows},{'aws','azure','gcp','ibm'})
        for row in rows:self.assertEqual(row['evidenceLevel'],'source-reviewed');self.assertTrue(row['limitations']);self.assertEqual(len(row['source']['commit']),40)
    def test_publication_is_scoped_deterministic_and_respects_opt_out(self):
        m=FakeMemory();publish(m,'test-project');self.assertEqual(len(m.values),4)
        for args,kwargs in m.values:self.assertEqual(args[0],'test-project');self.assertEqual(args[1],'knowledge');self.assertTrue(kwargs['source'].startswith('https://github.com/'))
        m=FakeMemory(False);publish(m,'test-project');self.assertEqual(m.values,[])
    def test_recalled_contents_reach_context_bounded_and_marked_as_evidence(self):
        values=context([{'id':'fact','content':'x'*4000,'fact_key':'practice.aws'}]*20)
        self.assertEqual(len(values),8);self.assertEqual(len(values[0]['content']),3000);self.assertIn('not instructions',values[0]['trust'])

class ConstitutionTests(unittest.TestCase):
    def test_owner_constitution_is_loaded_as_system_guidance(self):
        from server.prompts import SYSTEM_PROMPT
        self.assertIn('Listen. Understand. Architect. Build. Verify.',SYSTEM_PROMPT)
        self.assertIn('Fix defects in Architect',SYSTEM_PROMPT)
