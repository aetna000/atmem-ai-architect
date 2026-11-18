"""Deterministic JSON parsing rejects ambiguous keys and nonfinite numbers."""
import json


def strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    def constant(_):raise ValueError('Nonfinite JSON denied')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)
