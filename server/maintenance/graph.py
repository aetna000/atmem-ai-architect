"""Source-bound Terraform dependency discovery. No fetching or expression evaluation.

Edges point from a consumer to its dependency. Explicit remote bindings describe
already materialized source; they grant no permission and never assert publication.
"""
import json
import posixpath
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, model_validator

from .inventory import inventory, safe_path, validate_snapshot
from .models import Digest, Identifier, Record, Snapshot
from .store import digest


class Root(Record):
    id: Identifier
    snapshotId: Identifier
    directory: str = Field(default='.', max_length=1000)

    @model_validator(mode='after')
    def canonical(self):
        if self.directory != '.':
            safe_path(self.directory)
        return self


class ModuleBinding(Record):
    consumer: Identifier
    module: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=2000)
    version: str | None = Field(default=None, max_length=200)
    target: Identifier
    targetTreeDigest: Digest
    # A source/release name alone is insufficient: imported materialization needs
    # a recorded immutable upstream revision. Local directories use no binding.
    resolvedCommit: str = Field(pattern=r'^(?:[a-f0-9]{40}|[a-f0-9]{64})$')


def literal(expression):
    try:
        value = json.loads(expression)
        return value if isinstance(value, str) and '${' not in value and '%{' not in value else None
    except (ValueError, TypeError):
        return None


def discover(snapshots: list[Snapshot], roots: list[Root], bindings: list[ModuleBinding] | None = None):
    """Retain unknowns; validate selected-root/source identity before resolving edges."""
    bindings = bindings or []
    if not 1 <= len(snapshots) <= 100 or not 1 <= len(roots) <= 300 or len(bindings) > 1000:
        raise ValueError('Campaign discovery exceeds explicit source/root bounds')
    if sum(len(f.text.encode('utf-8')) for s in snapshots for f in s.files) > 64_000_000:
        raise ValueError('Campaign source exceeds 64 MB; no source was truncated')
    for source in snapshots:
        validate_snapshot(source)
    by_snapshot = {s.id: s for s in snapshots}
    by_root = {r.id: r for r in roots}
    if len(by_snapshot) != len(snapshots) or len(by_root) != len(roots):
        raise ValueError('Duplicate graph identity')
    locations = {}
    for root in roots:
        if root.snapshotId not in by_snapshot:
            raise ValueError('Root references unavailable source')
        key = (root.snapshotId, root.directory)
        if key in locations:
            raise ValueError('Duplicate selected Terraform root')
        locations[key] = root.id
    binding_map = {(b.consumer, b.module): b for b in bindings}
    if len(binding_map) != len(bindings) or any(b.consumer not in by_root or b.target not in by_root for b in bindings):
        raise ValueError('Ambiguous or unavailable dependency binding')
    reports = {ident: inventory(value) for ident, value in by_snapshot.items()}
    edges, nodes, unknowns, used = [], [], [], set()
    for root in sorted(roots, key=lambda r: r.id):
        source = by_snapshot[root.snapshotId]
        report = reports[root.snapshotId]
        selected = {p: d for p, d in report['files'].items()
                    if str(PurePosixPath(p).parent) == root.directory and p.endswith('.tf')}
        node = {'id': root.id, 'snapshotId': source.id, 'repositoryId': source.repositoryId,
                'directory': root.directory, 'treeDigest': source.treeDigest, 'commit': source.commit,
                'providers': [], 'aliases': [], 'findings': report['findings'],
                'locks': [{'path': f.path, 'sha256': f.sha256,
                           'selection': report['files'][f.path]['semantic'].get('provider', [])}
                          for f in source.files if f.path.endswith('.lock.hcl') and
                          str(PurePosixPath(f.path).parent) == root.directory]}
        nodes.append(node)
        if not selected:
            unknowns.append({'consumer': root.id, 'reason': 'root_has_no_hcl'})
        module_names = set()
        for path, document in sorted(selected.items()):
            for block in document['blocks']:
                attrs = {a['name']: a for a in block['attributes']}
                if block['type'] == 'terraform':
                    for child in block['blocks']:
                        if child['type'] == 'required_providers':
                            for attr in child['attributes']:
                                node['providers'].append({'localName': attr['name'], 'path': path, 'line': attr['line'],
                                    'expression': attr['expression'], 'members': attr.get('members', [])})
                if block['type'] == 'provider':
                    node['aliases'].append({'localName': block['labels'][0] if block['labels'] else '',
                                           'alias': literal(attrs.get('alias', {}).get('expression')),
                                           'path': path, 'line': block['line']})
                if block['type'] != 'module':
                    continue
                name = block['labels'][0] if len(block['labels']) == 1 else ''
                declaration = {'consumer': root.id, 'module': name, 'path': path, 'line': block['line'],
                               'start': block['start'], 'end': block['end'],
                               'source': literal(attrs.get('source', {}).get('expression')),
                               'version': literal(attrs.get('version', {}).get('expression')),
                               'providerMapping': attrs.get('providers', {}).get('expression')}
                reason, target = None, None
                if not name or name in module_names:
                    reason = 'duplicate_or_invalid_module'
                module_names.add(name)
                selected_source = declaration['source']
                if reason:
                    pass
                elif selected_source is None:
                    reason = 'dynamic_or_missing_source'
                elif selected_source.startswith(('./', '../')):
                    location = posixpath.normpath(posixpath.join(root.directory, selected_source))
                    if location == '..' or location.startswith('../'):
                        reason = 'local_source_outside_selected_repository'
                    else:
                        target = locations.get((root.snapshotId, location))
                        if target is None:
                            reason = 'local_module_not_selected'
                else:
                    binding = binding_map.get((root.id, name))
                    if binding:
                        used.add((root.id, name))
                        target_source = by_snapshot[by_root[binding.target].snapshotId]
                        if (binding.source != selected_source or binding.version != declaration['version'] or
                            binding.targetTreeDigest != target_source.treeDigest or
                            binding.resolvedCommit != target_source.commit):
                            reason = 'dependency_binding_stale'
                        else:
                            target = binding.target
                    else:
                        reason = 'remote_module_requires_materialization'
                if target is not None and reason is None:
                    edges.append({**declaration, 'dependency': target, 'resolution': 'selected_exact_source',
                                  'targetTreeDigest': by_snapshot[by_root[target].snapshotId].treeDigest})
                else:
                    unknowns.append({**declaration, 'reason': reason})
    if used != set(binding_map):
        raise ValueError('Unused dependency bindings cannot authorize graph scope')
    result = {'schemaVersion': 1, 'nodes': nodes, 'edges': edges, 'unknowns': unknowns,
              'parser': 'python-hcl2/7.3.1', 'bindings': [b.model_dump() for b in sorted(bindings, key=lambda b: (b.consumer, b.module))]}
    result['cycles'] = _cycles([r.id for r in roots], edges)
    result['digest'] = digest(result)
    return result


def _cycles(nodes, edges):
    # Bounded iterative reachability avoids recursion limits on adversarial chains.
    adjacency = {n: set() for n in nodes}
    for edge in edges:
        adjacency[edge['consumer']].add(edge['dependency'])
    reachable = {}
    for node in nodes:
        seen, pending = set(), list(adjacency[node])
        while pending:
            item = pending.pop()
            if item not in seen:
                seen.add(item)
                pending.extend(adjacency[item] - seen)
        reachable[node] = seen
    groups = set()
    for node in nodes:
        if node in reachable[node]:
            groups.add(tuple(sorted(n for n in nodes if n == node or n in reachable[node] and node in reachable[n])))
    return [list(group) for group in sorted(groups)]


def affected_waves(graph, changed):
    """Reverse dependency closure and dependency-first compatible review waves.

    A complete selected graph is required; absent repositories cannot be counted.
    Readiness here means discovery only, never checked patches or remote readiness.
    """
    expected = graph.get('digest')
    if expected != digest({k: v for k, v in graph.items() if k != 'digest'}):
        raise ValueError('Graph identity mismatch')
    nodes = {n['id'] for n in graph['nodes']}
    affected = set(changed)
    if not affected or not affected <= nodes:
        raise ValueError('Select known changed roots')
    while True:
        expanded = affected | {e['consumer'] for e in graph['edges'] if e['dependency'] in affected}
        if expanded == affected:
            break
        affected = expanded
    blockers = list(graph['unknowns'])
    blockers += [{'reason': 'dependency_cycle', 'roots': c} for c in graph['cycles']]
    blockers += [{'reason': 'blocked_source_construct', 'root': n['id'], 'finding': f}
                 for n in graph['nodes'] for f in n['findings'] if f['severity'] == 'blocked']
    waves, remaining = [], set(affected)
    while remaining:
        wave = sorted(n for n in remaining if not any(e['consumer'] == n and e['dependency'] in remaining for e in graph['edges']))
        if not wave:
            break
        waves.append(wave)
        remaining -= set(wave)
    return {'graphDigest': expected, 'affected': sorted(affected), 'waves': waves,
            'status': 'blocked' if blockers or remaining else 'discovered', 'blockers': blockers}
