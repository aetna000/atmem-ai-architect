import importlib.util
import os
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
os.environ["MAX_INPUT_BYTES"]="65536"
spec=importlib.util.spec_from_file_location("handler",Path(__file__).resolve().parents[1]/"build/block_746578742d7374617473/block_746578742d7374617473.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class HandlerTests(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(module.handler({"text":"one two\nthree"},None),{"wordCount":3,"characterCount":13})
        self.assertEqual(module.handler({"text":""},None),{"wordCount":0,"characterCount":0})
        self.assertEqual(module.handler({"text":"café 世界"},None),{"wordCount":2,"characterCount":7})
    def test_invalid_and_oversized(self):
        for value in [None,[],{}, {"text":1}, {"text":"secret","unexpected":True}, {"text":"é"*(module.MAX_INPUT_BYTES//2+1)}]:
            with self.assertRaises(ValueError):module.handler(value,None)
    def test_document_not_logged(self):
        output=StringIO()
        with redirect_stdout(output):module.handler({"text":"private synthetic document"},None)
        self.assertEqual(output.getvalue(),"")
