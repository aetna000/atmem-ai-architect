"""Bounded YAML front matter. Rules are data, never executable instructions."""
from datetime import date
import re
import yaml

GROUPS = ('budget', 'regions', 'data_residency', 'uptime', 'services', 'network')


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError('Policy keys must be unique strings')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def parse_policy(text):
    if not isinstance(text, str) or len(text.encode()) > 1_000_000:
        raise ValueError('Policy exceeds its 1 MB bound')
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        raise ValueError('architecture.md requires YAML front matter')
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
    if end is None:
        raise ValueError('Policy front matter must be closed')
    header = '\n'.join(lines[1:end])
    try:
        if any(isinstance(t, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)) for t in yaml.scan(header)):
            raise ValueError('YAML aliases and anchors are unsupported')
        value = yaml.load(header, Loader=UniqueLoader)
    except yaml.YAMLError:
        raise ValueError('Invalid architecture policy YAML') from None
    if not isinstance(value, dict) or value.get('schema') != 'atmem-architecture/v1':
        raise ValueError('Use schema atmem-architecture/v1')
    if set(value) - set(GROUPS) - {'schema', 'project', 'owner', 'exceptions'}:
        raise ValueError('Unknown policy group; it cannot be silently ignored')
    rules, ids = [], set()
    for group in GROUPS:
        items = value.get(group, [])
        if not isinstance(items, list) or len(items) > 200:
            raise ValueError('Each policy group must contain at most 200 rules')
        for rule in items:
            if not isinstance(rule, dict) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,99}', str(rule.get('id', ''))):
                raise ValueError('Every rule requires a stable bounded ID')
            if rule['id'] in ids or rule.get('severity', 'error') not in {'error', 'warning', 'info'}:
                raise ValueError('Rule IDs must be unique and severities explicit')
            fields={'budget':{'monthly_max','currency','environment','warn_at_percent'},'regions':{'allowed'},
                    'data_residency':{'data_classes','must_stay_in','applies_to'},'uptime':{'target_percent','requires'},
                    'services':{'approved','forbidden'},'network':{'rule','check'}}
            if set(rule)-fields[group]-{'id','severity'}:raise ValueError('Unknown rule field; it cannot be silently ignored')
            ids.add(rule['id']);rules.append((group, rule))
    if len(rules) > 200:
        raise ValueError('Policy exceeds 200 rules')
    exceptions = value.get('exceptions', [])
    if not isinstance(exceptions, list) or len(exceptions) > 200:
        raise ValueError('Exceptions must be a bounded list')
    exception_ids = set()
    for exception in exceptions:
        if not isinstance(exception, dict) or set(exception) - {'id', 'rule_id', 'reason', 'approved_by', 'expires', 'resource_addresses'}:
            raise ValueError('Invalid exception fields')
        if (not isinstance(exception.get('id'),str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,99}',exception['id']) or exception['id'] in exception_ids or exception.get('rule_id') not in ids
            or not isinstance(exception.get('reason'), str) or not exception['reason'].strip()
            or not isinstance(exception.get('approved_by'), str) or not exception['approved_by'].strip()):
            raise ValueError('Exceptions require unique ID, known rule, reason and approver')
        date.fromisoformat(str(exception.get('expires', '')))
        if 'resource_addresses' in exception and (not isinstance(exception['resource_addresses'], list) or
                any(not isinstance(a, str) for a in exception['resource_addresses'])):
            raise ValueError('Exception scope must list exact resource addresses')
        exception_ids.add(exception['id'])
    adrs = re.findall(r'^##\s+(ADR-\d+)\b', '\n'.join(lines[end+1:]), re.M)
    if len(adrs)>200 or any(len(a)>32 for a in adrs):raise ValueError('ADR count or ID exceeds bounds')
    if len(adrs) != len(set(adrs)):
        raise ValueError('ADR IDs must be unique')
    return {'rules': rules, 'exceptions': exceptions, 'adrs': adrs, 'lines': lines}
