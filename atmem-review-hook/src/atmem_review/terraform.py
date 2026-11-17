"""Interpret supplied desired-state JSON without running Terraform or providers."""
import re

UNKNOWN = object()


def normalized(address):
    return re.sub(r'\[(?:\d+|"(?:\\.|[^"\\])*")\]', '', address)


def value_at(values, mask, path):
    for part in path.split('.'):
        if mask is True:
            return UNKNOWN
        mask = mask.get(part, False) if isinstance(mask, dict) else False
        if not isinstance(values, dict) or part not in values:
            return UNKNOWN
        values = values[part]
    def unresolved(v):
        return v is True or isinstance(v,dict) and any(unresolved(x) for x in v.values()) or isinstance(v,list) and any(unresolved(x) for x in v)
    return UNKNOWN if unresolved(mask) or values is None else values


def resources(plan):
    if not isinstance(plan, dict) or not str(plan.get('format_version', '')).startswith('1.'):
        raise ValueError('Only Terraform show JSON format 1.x is supported')
    found, configs = {}, {}
    def walk(module, prefix='', depth=0):
        if depth > 30 or not isinstance(module, dict):
            raise ValueError('Terraform module shape/depth is unsupported')
        for item in module.get('resources', []):
            if item.get('mode', 'managed') != 'managed':continue
            address = item.get('address')
            if not isinstance(address, str) or len(address)>2000 or not isinstance(item.get('type'), str) or len(item['type'])>200 or address in found:
                raise ValueError('Resource identities must be unique and explicit')
            found[address] = {**item, 'values': item.get('values', {}), 'unknown': item.get('sensitive_values', {}), 'complete': True}
            if len(found) > 10000:raise ValueError('Terraform exceeds 10000 resources')
        for child in module.get('child_modules', []):walk(child, depth=depth+1)
    root = plan.get('planned_values', {}).get('root_module')
    if root is not None:walk(root)
    changes = set()
    for item in plan.get('resource_changes', []):
        if item.get('mode', 'managed') != 'managed':continue
        address = item.get('address');change = item.get('change', {})
        if not isinstance(address, str) or len(address)>2000 or address in changes or not isinstance(item.get('type'), str) or len(item['type'])>200:
            raise ValueError('Change identities must be unique and explicit')
        changes.add(address)
        actions = change.get('actions')
        if not isinstance(actions, list) or not actions or set(actions)-{'no-op','create','update','delete','read','forget'}:
            raise ValueError('Unsupported Terraform change action')
        if set(actions) <= {'delete','forget'}:
            found.pop(address, None);continue
        if not isinstance(change.get('after'), dict):
            raise ValueError('Future managed resource values must be supplied')
        if address in found:
            # Known values must agree; never select the more convenient input.
            for key, val in found[address]['values'].items():
                other = change['after'].get(key, UNKNOWN)
                if other is not UNKNOWN and not change.get('after_unknown', {}).get(key) and other != val:
                    raise ValueError('Conflicting planned_values and change.after')
        found[address] = {**item, 'values': change['after'], 'unknown': _merge_mask(found.get(address,{}).get('unknown',{}),_merge_mask(change.get('after_unknown', {}),change.get('after_sensitive', {}))), 'complete': root is not None}
    if len(found) > 10000:raise ValueError('Terraform exceeds 10000 resources')
    def configuration(module, prefix='', depth=0):
        if depth > 30:raise ValueError('Configuration module depth exceeds bounds')
        for item in module.get('resources', []):
            address = item.get('address', '')
            if address:configs[normalized(prefix+address)] = item
        for name, call in module.get('module_calls', {}).items():
            if isinstance(call.get('module'), dict):configuration(call['module'], prefix+'module.'+name+'.', depth+1)
    configuration(plan.get('configuration', {}).get('root_module', {}))
    for item in found.values():item['config'] = configs.get(normalized(item['address']), {})
    return list(found.values()), root is not None and plan.get('complete', True) is True and not plan.get('deferred_changes')


def region(item, plan):
    if item['unknown'] is True:return UNKNOWN,'region'
    direct = value_at(item['values'], item['unknown'], 'region')
    if direct is not UNKNOWN:return direct, 'region'
    if 'region' in item['values'] or isinstance(item['unknown'],dict) and item['unknown'].get('region'):
        return UNKNOWN,'region'
    key = item['config'].get('provider_config_key')
    providers = plan.get('configuration', {}).get('provider_config', {})
    # A sole unaliased AWS provider is unambiguous; a sole alias is not a default.
    if key is None and item['type'].startswith('aws_') and set(providers) == {'aws'}:key='aws'
    provider = providers.get(key, {})
    expression = provider.get('expressions', {}).get('region', {})
    result = expression.get('constant_value', UNKNOWN)
    return result, 'configuration.provider_config.'+str(key)+'.expressions.region.constant_value'


def _merge_mask(left,right):
    if left is True or right is True:return True
    if isinstance(left,dict) or isinstance(right,dict):
        a=left if isinstance(left,dict) else {};b=right if isinstance(right,dict) else {}
        return {k:_merge_mask(a.get(k,False),b.get(k,False)) for k in a.keys()|b.keys()}
    if isinstance(left,list) or isinstance(right,list):return True
    return False
