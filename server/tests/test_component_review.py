import unittest
from pydantic import ValidationError
from server.contracts import ArchitectResponse,ChatRequest

class ComponentReviewContractTests(unittest.TestCase):
    def test_scoped_review_contract_and_origin(self):
        response=ArchitectResponse.model_validate({'message':'A design question remains.','componentReview':{'componentId':'browser','summary':'Ownership is clear.','questions':['How is identity recovered?']}})
        self.assertEqual(response.componentReview.componentId,'browser')
        request=ChatRequest(message='Review browser',provider='codex',model='default',origin='block-review',project={'version':1,'revision':1,'name':'Review','nodes':[],'edges':[]})
        self.assertEqual(request.origin,'block-review')

    def test_empty_oversize_and_unbounded_questions_are_rejected(self):
        for questions in [[''],['x'*1001],['Q']*7]:
            with self.assertRaises(ValidationError):
                ArchitectResponse.model_validate({'message':'Review','componentReview':{'componentId':'browser','summary':'Review','questions':questions}})
