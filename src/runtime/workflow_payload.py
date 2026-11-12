"""Versioned bounded application data contracts, independent of domain/provider.

This is a small closed contract language, not a JSON Schema implementation.
Operator-selected contracts describe data, never roles, executable validation,
destinations or transitions. Domain semantic checks remain the adapter's duty.
"""
from dataclasses import dataclass
import hashlib
import json
import re


def encoded(value):
    def exact(item, depth=0):
        if depth > 32: raise ValueError('Application JSON exceeds its nesting boundary')
        if type(item) is dict:
            if any(type(k) is not str for k in item): raise ValueError('Application object keys must be strings')
            for child in item.values(): exact(child, depth + 1)
        elif type(item) is list:
            for child in item: exact(child, depth + 1)
        elif type(item) not in {str, int, bool, type(None)}:
            raise ValueError('Use exact application JSON types; decimals require an explicit string contract')
    exact(value)
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise ValueError('Invalid bounded application JSON') from None
    if len(raw) > 64000:
        raise ValueError('Application JSON exceeds its byte boundary')
    return raw


def schema(value, depth=0, budget=None):
    if budget is None: budget = [256]
    budget[0] -= 1
    if depth > 8 or budget[0] < 0 or type(value) is not dict:
        raise ValueError('Application contract exceeds its structural boundary')
    kind = value.get('type')
    shapes = {'object': {'type', 'properties', 'required'}, 'array': {'type', 'items', 'maxItems'},
              'string': {'type', 'minBytes', 'maxBytes'}, 'integer': {'type', 'minimum', 'maximum'},
              'boolean': {'type'}, 'enum': {'type', 'values'}}
    if type(kind) is not str or kind not in shapes or set(value) != shapes[kind]:
        raise ValueError('Use the closed application contract language')
    if kind == 'object':
        properties, required = value['properties'], value['required']
        if (type(properties) is not dict or not 1 <= len(properties) <= 32 or
            any(type(k) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,79}', k) for k in properties) or
            type(required) is not list or any(type(k) is not str for k in required) or
            len(required) != len(set(required)) or not set(required) <= set(properties)):
            raise ValueError('Use bounded exact object fields')
        for item in properties.values(): schema(item, depth + 1, budget)
    elif kind == 'array':
        if type(value['maxItems']) is not int or not 1 <= value['maxItems'] <= 64:
            raise ValueError('Use a bounded array')
        schema(value['items'], depth + 1, budget)
    elif kind == 'string':
        if any(type(value[k]) is not int for k in ['minBytes', 'maxBytes']) or not 0 <= value['minBytes'] <= value['maxBytes'] <= 64000:
            raise ValueError('Use exact UTF-8 byte limits')
    elif kind == 'integer':
        if any(type(value[k]) is not int for k in ['minimum', 'maximum']) or not -(2**53 - 1) <= value['minimum'] <= value['maximum'] <= 2**53 - 1:
            raise ValueError('Use exact portable integer limits')
    elif kind == 'enum':
        items = value['values']
        if (type(items) is not list or not 1 <= len(items) <= 64 or
            any(type(item) is not str or not 1 <= len(item.encode('utf-8')) <= 256 for item in items) or len(items) != len(set(items))):
            raise ValueError('Use a bounded distinct string enumeration')


def conforms(rule, value):
    kind = rule['type']
    valid = False
    if kind == 'object':
        valid = (type(value) is dict and set(rule['required']) <= set(value) <= set(rule['properties']))
        if valid:
            for key, item in value.items(): conforms(rule['properties'][key], item)
    elif kind == 'array':
        valid = type(value) is list and len(value) <= rule['maxItems']
        if valid:
            for item in value: conforms(rule['items'], item)
    elif kind == 'string':
        valid = type(value) is str and rule['minBytes'] <= len(value.encode('utf-8')) <= rule['maxBytes']
    elif kind == 'integer': valid = type(value) is int and rule['minimum'] <= value <= rule['maximum']
    elif kind == 'boolean': valid = type(value) is bool
    elif kind == 'enum': valid = type(value) is str and value in rule['values']
    if not valid: raise ValueError('Application payload does not match its owned contract')


@dataclass(frozen=True, init=False)
class PayloadContract:
    _encoded: bytes

    def __init__(self, value):
        raw = encoded(value)
        copied = json.loads(raw)
        if (type(copied) is not dict or set(copied) != {'version', 'id', 'source', 'result'} or
            type(copied['version']) is not int or copied['version'] != 1 or
            type(copied['id']) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,79}', copied['id'])):
            raise ValueError('Use a versioned owned application payload contract')
        budget = [256]
        for side in ['source', 'result']:
            schema(copied[side], budget=budget)
            if copied[side]['type'] != 'object': raise ValueError('Application boundaries require object payloads')
        object.__setattr__(self, '_encoded', raw)

    @property
    def sha256(self): return hashlib.sha256(self._encoded).hexdigest()

    def fields(self, side):
        if side not in {'source', 'result'}: raise ValueError('Use an application input or result boundary')
        return tuple(json.loads(self._encoded)[side]['properties'])

    def validate(self, side, value):
        if side not in {'source', 'result'}: raise ValueError('Use an application input or result boundary')
        # Round trip before validation: no caller mutation can change the bytes
        # validated for persistence. No clipping, coercion or default insertion.
        copied = json.loads(encoded(value))
        conforms(json.loads(self._encoded)[side], copied)
        return copied
