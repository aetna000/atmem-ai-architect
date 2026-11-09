import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from server.generation_lint import lint_generated

class GenerationLintTests(unittest.TestCase):
    def test_diagnostics_are_not_lost_and_cloud_credentials_are_not_inherited(self):
        with tempfile.TemporaryDirectory() as root,patch('server.generation_lint.subprocess.run',return_value=subprocess.CompletedProcess([],2,json.dumps({'issues':[{'message':'unused variable'}],'errors':[]}),'ignored')) as run:
            report=lint_generated(root,'/operator/tflint')
            self.assertFalse(report['passed']);self.assertEqual(report['issues'][0]['message'],'unused variable')
            self.assertNotIn('AWS_SECRET_ACCESS_KEY',run.call_args.kwargs['env'])
            self.assertTrue(any(a.startswith('--config='+root) for a in run.call_args.args[0]))
    def test_clean_and_malformed_reports(self):
        for stdout,code,passed in [('{"issues":[],"errors":[]}',0,True),('not JSON',0,False),('{"issues":[],"errors":[]}',1,False)]:
            with self.subTest(stdout=stdout,code=code),tempfile.TemporaryDirectory() as root,patch('server.generation_lint.subprocess.run',return_value=subprocess.CompletedProcess([],code,stdout,'')):
                self.assertEqual(lint_generated(root,'/operator/tflint')['passed'],passed)
