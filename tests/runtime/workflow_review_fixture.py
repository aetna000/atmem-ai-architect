"""Evaluator-owned deterministic domains, never shipped as application recipes."""
def parcel_result(source, result):
    if result['massMilligrams'] != source['massGrams'] * 1000:
        raise ValueError('Mass is source-derived')
    expected = 'express' if source['massGrams'] >= 500 or source['priority'] == 'rush' else 'standard'
    if result['lane'] != expected:
        raise ValueError('Routing is source-derived')


def audio_result(source, result):
    if result['chargeUnits'] != (source['durationSeconds'] + 59) // 60:
        raise ValueError('Billing is source-derived')


def transforming_validator(source, result):
    result['reviewNote'] = result['reviewNote'].strip()


def returning_validator(source, result):
    return result


def accepting_validator(source, result):
    return None


def definition(domain):
    def obj(fields): return {'type': 'object', 'properties': fields, 'required': list(fields)}
    def integer(low, high): return {'type': 'integer', 'minimum': low, 'maximum': high}
    note = {'type': 'string', 'minBytes': 0, 'maxBytes': 512}
    if domain == 'parcel-weighing':
        source = obj({'massGrams': integer(0, 1000000000),
                      'priority': {'type': 'enum', 'values': ['regular', 'rush']}, 'note': note})
        result = obj({'massMilligrams': integer(0, 1000000000000),
                      'lane': {'type': 'enum', 'values': ['standard', 'express']}, 'reviewNote': note})
    elif domain == 'audio-caption':
        source = obj({'durationSeconds': integer(0, 86400), 'verbatim': note})
        result = obj({'chargeUnits': integer(0, 1440), 'caption': note})
    else:
        raise ValueError('Unknown evaluator domain')
    return {'version': 1, 'id': domain, 'source': source, 'result': result}
