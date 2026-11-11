import unittest
from server.validation_applicability import FileApplicability,matches


class ApplicabilityTests(unittest.TestCase):
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
