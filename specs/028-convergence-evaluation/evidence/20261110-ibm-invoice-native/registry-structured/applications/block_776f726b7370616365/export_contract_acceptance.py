"""Acceptance inputs derived from the actual emitted schema, never a smaller demo."""
from pathlib import Path
import json
from structured_output import _object

def actual_contract():
    path=Path(__file__).parent/'output-contract.json'
    if not path.is_file():path=Path('/app/output-contract.json')
    # Missing emitted evidence is a failure, not a skipped test.
    contract=json.loads(path.read_text(),object_pairs_hook=_object)
    expected={}
    for field in contract['fields']:
        if field.get('values'):value=field['values'][0]
        elif field['type']=='string':value='X'
        elif field['type']=='boolean':value=True
        else:value=0
        expected[field['name']]=value
    return contract,expected
