import unittest
from pydantic import ValidationError
from server.contracts import BuildSpec,VerificationCase

class VerificationCaseTests(unittest.TestCase):
    def case(self):
        return dict(id='same-key',name='Replay one request',category='contract',requirementIds=['once'],environment='Local adapter with a transaction store.',setup='An empty ledger and two clients.',input='Same key K and payload P from both clients.',action='Submit concurrently, then read receipt K.',expected='One durable effect and the same receipt for both clients.',evidence='Both outcomes, ledger row and transaction trace.')
    def test_declared_cases_preserve_inputs_without_execution_claims(self):
        case=self.case();self.assertEqual(BuildSpec(verificationCases=[case]).verificationCases[0].model_dump(exclude_none=True),case)
    def test_incomplete_duplicate_and_claimed_pass_cases_reject(self):
        for field,value in [('expected',' '),('category','passed'),('requirementIds',['once','once']),('status','passed')]:
            case=self.case();case[field]=value
            with self.assertRaises(ValidationError):VerificationCase(**case)
        with self.assertRaises(ValidationError):BuildSpec(verificationCases=[self.case(),self.case()])
        with self.assertRaises(ValidationError):BuildSpec(verificationCases=[])
