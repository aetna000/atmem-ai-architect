import unittest
from pydantic import ValidationError
from server.contracts import Data

class NoteContractTests(unittest.TestCase):
    def test_blank_note_does_not_block_chat(self):
        for text in ('', ' ', 'Confirm retention'):
            self.assertEqual(Data(label=text, kind='note', provider='tools').label, text)
    def test_components_still_require_names(self):
        for text in ('', ' '):
            with self.assertRaises(ValidationError):
                Data(label=text, kind='resource', provider='aws')
