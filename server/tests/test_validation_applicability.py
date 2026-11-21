import unittest
from server.validation_applicability import FileApplicability,matches


class ApplicabilityTests(unittest.TestCase):
    def test_exact_dependency_lock_selection_transfers_without_domain_or_provider_dispatch(self):
        import hashlib
        contents=[b'client_sdk==1.0\n',b'other_sdk==2.0\n']
        rules=[FileApplicability.parse({'anyOf':['**/test_*.py'],'anyFileSha256':[{'pattern':'**/requirements.lock','sha256':hashlib.sha256(content).hexdigest()}]})for content in contents]
        for domain in ['museum/catalog','weather/instruments','renamed']:
            files=[{'path':domain+'/test_rules.py','kind':'file'},{'path':domain+'/requirements.lock','kind':'file','sha256':hashlib.sha256(contents[0]).hexdigest()}]
            self.assertEqual([rule.assess(files)['applies']for rule in rules],[True,False])
            files[-1]['sha256']=hashlib.sha256(contents[0]+b'changed').hexdigest()
            self.assertEqual([rule.assess(files)['applies']for rule in rules],[False,False])

    def test_digest_rules_require_exact_regular_file_paths_and_preserve_legacy_shape(self):
        legacy=FileApplicability.parse({'anyOf':['**/test_*.py']})
        self.assertEqual(legacy.public(),{'anyOf':('**/test_*.py',),'allOf':(),'noneOf':()})
        rule=FileApplicability.parse({'anyOf':['**/test_*.py'],'anyFileSha256':[{'pattern':'**/requirements.lock','sha256':'a'*64}]})
        for file in [{'path':'requirements.lock','kind':'symlink','sha256':'a'*64},{'path':'requirements.lock','kind':'file'},{'path':'different.lock','kind':'file','sha256':'a'*64}]:
            self.assertFalse(rule.assess([{'path':'test_unit.py','kind':'file'},file])['applies'])
        self.assertFalse(rule.assess([{'path':'requirements.lock','kind':'file','sha256':'a'*64}])['applies'])
        self.assertEqual(rule.public()['anyFileSha256'],[{'pattern':'**/requirements.lock','sha256':'a'*64}])

    def test_digest_rules_reject_ambiguous_unbounded_or_executable_operator_inputs(self):
        for value in [None,{},'a'*64,{'pattern':'../requirements.lock','sha256':'a'*64},{'pattern':'requirements.lock','sha256':'A'*64},{'pattern':'requirements.lock','sha256':'a'*63},{'pattern':'requirements.lock','sha256':'a'*64,'command':['/bin/sh']}]:
            with self.subTest(value=value),self.assertRaises(ValueError):FileApplicability.parse({'anyOf':['**/test_*.py'],'anyFileSha256':[value]})
        item={'pattern':'requirements.lock','sha256':'a'*64}
        for values in [[item,item],[{**item,'sha256':format(n,'064x')}for n in range(17)]]:
            with self.assertRaises(ValueError):FileApplicability.parse({'anyOf':['**/test_*.py'],'anyFileSha256':values})

    def test_segment_and_recursive_matching_including_zero_segments(self):
        for pattern,name,expected in [
            ('*.py','test_a.py',True),('*.py','tests/test_a.py',False),
            ('**/test_*.py','test_a.py',True),('**/test_*.py','a/tests/test_b.py',True),
            ('tests/**/test_*.py','tests/test_a.py',True),('tests/**/test_*.py','other/tests/test_a.py',False),
            ('**/a/**/b/*.mjs','x/a/b/a/b/x.mjs',True),
            ('**/*.test.mjs','tests/x.test.mjs',True),('**/*.test.mjs','tests/x.test.js',False)]:
            with self.subTest(pattern=pattern,name=name):self.assertEqual(matches(pattern,name),expected)

    def test_rejects_unbounded_ambiguous_or_command_shaped_rules(self):
        for value in [{},{'anyOf':[]},{'anyOf':'*.py'},{'anyOf':['/tmp/*.py']},
            {'anyOf':['../*.py']},{'anyOf':['a//b']},{'anyOf':['a/**b']},
            {'anyOf':['a\\b']},{'anyOf':['a\nb']},{'anyOf':[['*.py']]},
            {'anyOf':['*.py']*2},{'anyOf':['*.py'],'command':['/bin/sh']}]:
            with self.subTest(value=value),self.assertRaises(ValueError):FileApplicability.parse(value)

    def test_transfers_across_domains_and_keeps_missing_and_exclusions_explicit(self):
        rule=FileApplicability.parse({'anyOf':['**/*.test.mjs','**/*.test.js'],'allOf':['package.json'],'noneOf':['UNSUPPORTED_RUNTIME']})
        def assess(*names):return rule.assess([{'path':name,'kind':'file'} for name in names])
        for name in ['museum/tests/catalog.test.mjs','weather/stations.test.js']:
            self.assertTrue(assess(name,'package.json')['applies'])
        self.assertFalse(assess('museum/tests/catalog.test.mjs')['applies'])
        self.assertEqual(assess('catalog.test.mjs')['missingAllOf'],['package.json'])
        self.assertEqual(assess('catalog.test.mjs','package.json','UNSUPPORTED_RUNTIME')['matchedNoneOf'],['UNSUPPORTED_RUNTIME'])
        self.assertFalse(rule.assess([{'path':'example.test.mjs','kind':'directory'},{'path':'package.json','kind':'file'}])['applies'])
