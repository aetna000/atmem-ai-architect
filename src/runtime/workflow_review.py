"""Explicit review/access/semantic policy supplied by trusted application code.

No domain fields, provider selection, executable loading or user configuration.
Semantic validators may reject data, never normalize it. Their implementation and
declared source dependencies are approval-bound; this is not a Python sandbox or
proof that a trusted validator is pure, bounded, or declares every dependency.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import types
if __package__:
    from .workflow_payload import PayloadContract, encoded
else:
    from workflow_payload import PayloadContract, encoded


@dataclass(frozen=True, init=False)
class ReviewPolicy:
    _encoded: bytes
    _sources: tuple
    _validator: object
    _payload: PayloadContract

    def __init__(self, payload, *, id, editable_fields, read_scope='owner',
                 inspection_ttl_seconds=300, validator=None, validation_sources=()):
        if type(payload) is not PayloadContract:
            raise ValueError('Supply the exact owned payload contract')
        if type(id) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,79}', id):
            raise ValueError('Use a versioned owned review policy identity')
        fields = payload.fields('result')
        if (type(editable_fields) not in {list, tuple} or
            any(type(field) is not str for field in editable_fields) or
            len(set(editable_fields)) != len(editable_fields) or not set(editable_fields) <= set(fields)):
            raise ValueError('Declare the editable top-level result fields explicitly')
        if type(read_scope) is not str or read_scope not in {'owner', 'account'}:
            raise ValueError('Use an explicit application read scope')
        if inspection_ttl_seconds is not None and (type(inspection_ttl_seconds) is not int or not 1 <= inspection_ttl_seconds <= 3600):
            raise ValueError('Use a bounded inspection lifetime or explicit None')
        if type(validation_sources) not in {list, tuple, dict} or len(validation_sources) > 32:
            raise ValueError('Declare bounded trusted validator source dependencies')
        if validator is not None and (type(validator) is not types.FunctionType or validator.__closure__):
            raise ValueError('Supply a trusted module-level semantic validator, not executable data')
        if (validator is None) != (not validation_sources):
            raise ValueError('A semantic validator requires its explicit source dependencies')
        sources = []
        entries = validation_sources.items() if type(validation_sources) is dict else [(Path(source).name,source) for source in validation_sources]
        labels = set()
        for label, source in entries:
            if (type(label) is not str or len(label)>512 or '\\' in label or
                PurePosixPath(label).is_absolute() or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,127}',part) or part in {'.','..'} for part in label.split('/'))):
                raise ValueError('Use explicit portable relative validator dependency labels')
            if label in labels:raise ValueError('Use explicit relative source labels for duplicate filenames')
            labels.add(label)
            path = Path(source)
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 1048576:
                raise ValueError('Use bounded regular validator source files')
            path = path.resolve()
            sources.append((label, path, hashlib.sha256(path.read_bytes()).hexdigest()))
        if validator is not None and Path(validator.__code__.co_filename).resolve() not in {path for _, path, _ in sources}:
            raise ValueError('The semantic validator implementation must be source-bound')
        mechanism = Path(__file__).resolve()
        mechanism_sha256 = hashlib.sha256(mechanism.read_bytes()).hexdigest()
        definition = {'version': 1, 'id': id, 'payloadContractSha256': payload.sha256,
                      'mechanismSha256': mechanism_sha256,
                      'editableFields': sorted(editable_fields), 'readScope': read_scope,
                      'inspectionTtlSeconds': inspection_ttl_seconds,
                      'validator': None if validator is None else {
                          'entrypoint': validator.__qualname__,
                          'sources': {label: sha for label, _, sha in sorted(sources)}}}
        object.__setattr__(self, '_encoded', encoded(definition))
        object.__setattr__(self, '_sources', tuple((path,sha) for _,path,sha in sources)+((mechanism, mechanism_sha256),))
        object.__setattr__(self, '_validator', validator)
        object.__setattr__(self, '_payload', payload)

    @property
    def data(self): return json.loads(self._encoded)

    @property
    def sha256(self): return hashlib.sha256(self._encoded).hexdigest()

    def ensure_current(self):
        for path, sha in self._sources:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 1048576 or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise ValueError('Review validator sources changed; qualify a new policy binding')

    def validate_result(self, source, result):
        self.ensure_current()
        original = self._payload.validate('source', source)
        value = self._payload.validate('result', result)
        if self._validator is not None:
            before = (encoded(original), encoded(value))
            returned = self._validator(original, value)
            if returned is not None or (encoded(original), encoded(value)) != before:
                raise ValueError('Semantic validation must only accept or reject, never transform data')
        return value

    def validate_edit(self, source, previous, result):
        value = self.validate_result(source, result)
        previous = self._payload.validate('result', previous)
        editable = set(self.data['editableFields'])
        if encoded({k: v for k, v in previous.items() if k not in editable}) != encoded({k: v for k, v in value.items() if k not in editable}):
            raise ValueError('Only explicitly editable result fields may change')
        return value
