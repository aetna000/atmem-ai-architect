"""Deterministic diagram review, shared across solutions and model providers."""

import re

_UNKNOWN = re.compile(r'^(?:tbd|tbc|unknown|unspecified|placeholder|pending confirmation)\b|^/proposed(?:/|$)', re.I)


def _fields(record):
    return {item.name.casefold().strip(): item.value.strip() for item in record.details}


def _check_fields(record, required):
    known = _fields(record)
    missing = [name for name in required if not known.get(name.casefold())]
    unresolved = [name for name in required if _UNKNOWN.search(known.get(name.casefold(), ''))]
    issues = []
    if missing:
        issues.append(f'{record.name}: supply or confirm ' + ', '.join(missing) + '.')
    if unresolved:
        issues.append(f'{record.name}: identify the owner and evidence needed to confirm ' + ', '.join(unresolved) + '.')
    return issues


def _columns(record):
    return {line.split()[0] for line in _fields(record).get('columns', '').splitlines() if line.strip()}


def _keys(value):
    return [part.strip() for part in value.split(',') if part.strip()]


def review(views, elements, relations, skills):
    findings = {}
    for view in views:
        issues = []
        nodes = [elements[key] for key in view.elementIds]
        edges = [relations[key] for key in view.relationIds]
        kind = view.kind
        skill = skills[kind]
        if not nodes:
            findings[kind] = ['No project elements. Identify the missing evidence, its owner and the affected scope.']
            continue

        def fields(record):
            return {item.name: item.value for item in record.details}

        for node in nodes:
            required = skill['expectedElementFields'].get(node.kind, [])
            issues.extend(_check_fields(node, required))
            if node.kind == 'table' and kind == 'erd':
                primary = _keys(_fields(node).get('primary key', ''))
                if any(column not in _columns(node) for column in primary):
                    issues.append(f'{node.name}: match the primary key to the declared columns.')

        node_kinds = {row.kind for row in nodes}
        if kind == 'context' and sum(row.kind=='system' for row in nodes) != 1:
            issues.append('Use exactly one focal system.')
        if kind in {'state', 'workflow'} and 'start' not in node_kinds:
            issues.append('Identify the initial state or start.')
        if kind == 'workflow' and 'end' not in node_kinds:
            issues.append('Identify the terminal outcomes.')
        if not edges and kind not in {'capability', 'layer', 'domain', 'journey', 'migration', 'erd'}:
            issues.append('Add the supported relationships, or explain the missing connection evidence.')

        for edge in edges:
            known = fields(edge)
            source = elements[edge.fromId]
            target = elements[edge.toId]
            required = skill.get('expectedRelationFields', {}).get(edge.kind, [])
            if source.kind == 'decision' and edge.kind == 'control-flow':
                required = [*required, 'Guard']
            issues.extend(_check_fields(edge, required))
            if edge.kind == 'foreign-key':
                left = _keys(_fields(edge).get('from columns', ''))
                right = _keys(_fields(edge).get('to columns', ''))
                if not left or len(left) != len(right) or not set(left) <= _columns(source) or not set(right) <= _columns(target):
                    issues.append(f'{edge.name}: match both foreign-key column lists to their declared tables.')
            if kind == 'data-flow' and 'process' not in {source.kind,target.kind}:
                issues.append(f'{edge.name}: route the data through a process.')
            if edge.kind == 'routes-to':
                a, b = fields(source), fields(target)
                path = known.get('Rewrite') or a.get('Path')
                if not (a.get('Method') and b.get('Method') and a['Method'].upper()==b['Method'].upper() and path and path==b.get('Path')):
                    issues.append(f'{edge.name}: reconcile the route method and path with its operation.')
        findings[kind] = list(dict.fromkeys(issues))
    return findings
