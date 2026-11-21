"""Provider-neutral flat output boundary. Never executes model-supplied actions."""
import json
import math

class InvalidModelOutput(ValueError):
    pass

def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidModelOutput('Duplicate field')
        result[key] = value
    return result

def decode_output(text, fields):
    if not isinstance(text, str):
        raise InvalidModelOutput('Expected JSON text')
    try:
        if len(text.encode('utf-8')) > 131072:
            raise InvalidModelOutput('Oversized output')
        value = json.loads(text, object_pairs_hook=_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(InvalidModelOutput('Non-finite number')))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise InvalidModelOutput('Invalid JSON output') from None
    if not isinstance(value, dict) or set(value) != {f['name'] for f in fields}:
        raise InvalidModelOutput('Output fields do not match contract')
    for field in fields:
        item = value[field['name']]
        kind = field['type']
        if kind == 'string':
            if not isinstance(item, str) or len(item) > field.get('maxLength', 4096):
                raise InvalidModelOutput('Invalid string output')
            try:
                item.encode('utf-8')
            except UnicodeError:
                raise InvalidModelOutput('Invalid Unicode output') from None
            if 'values' in field and item not in field['values']:
                raise InvalidModelOutput('Value outside enumeration')
        elif kind == 'boolean':
            if type(item) is not bool:
                raise InvalidModelOutput('Invalid boolean output')
        elif kind == 'number':
            if type(item) not in (int, float) or abs(item) > 1e308 or not math.isfinite(item):
                raise InvalidModelOutput('Invalid numeric output')
        else:
            raise InvalidModelOutput('Unsupported output contract')
    return value
