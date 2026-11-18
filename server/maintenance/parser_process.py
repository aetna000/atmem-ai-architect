"""Bounded parser process: input is data, expressions are never evaluated."""
import json
import os
import sys

import hcl2
from lark import Tree


def children(node, kind):
    return [c for c in node.children if isinstance(c, Tree) and str(c.data) == kind]


def content(node, source):
    return source[node.meta.start_pos:node.meta.end_pos]


def attribute(node, source):
    name = content(children(node, 'identifier')[0], source)
    expression = next(c for c in reversed(node.children) if isinstance(c, Tree))
    result = {'name': name, 'start': node.meta.start_pos, 'end': node.meta.end_pos,
              'line': node.meta.line, 'expression': content(expression, source),
              'expressionStart': expression.meta.start_pos, 'expressionEnd': expression.meta.end_pos}
    terms = children(expression, 'tuple')
    if str(expression.data) == 'expr_term' and len(terms) == 1:
        result['tuple'] = [{'start': c.meta.start_pos, 'end': c.meta.end_pos,
                            'text': content(c, source)} for c in terms[0].children
                           if isinstance(c, Tree) and str(c.data) != 'new_line_or_comment']
    objects = children(expression, 'object')
    if len(objects) == 1:
        result['members'] = []
        for item in children(objects[0], 'object_elem'):
            key = children(item, 'object_elem_key')[0]
            value = next(c for c in reversed(item.children) if isinstance(c, Tree))
            result['members'].append({'name': content(key, source).strip('"'),
                                      'expression': content(value, source),
                                      'start': value.meta.start_pos, 'end': value.meta.end_pos})
    return result


def block(node, source):
    identifiers = children(node, 'identifier')
    labels = []
    for label in children(node, 'string'):
        raw = content(label, source)
        labels.append(json.loads(raw))
    body = children(node, 'body')[0]
    return {'type': content(identifiers[0], source), 'labels': labels,
            'start': node.meta.start_pos, 'end': node.meta.end_pos, 'line': node.meta.line,
            'attributes': [attribute(c, source) for c in children(body, 'attribute')],
            'blocks': [block(c, source) for c in children(body, 'block')]}


def parse(source):
    # HCL allows an EOF line comment. This parser version requires a final
    # newline for that token; add only a parser sentinel, never edit source bytes.
    parse_source = source if source.endswith('\n') else source + '\n'
    tree = hcl2.parses(parse_source)
    body = children(tree, 'body')[0]
    return {'blocks': [block(c, source) for c in children(body, 'block')],
            'semantic': hcl2.loads(parse_source),
            'comments': [{'start': c.meta.start_pos, 'end': c.meta.end_pos, 'text': content(c, source)}
                         for c in tree.iter_subtrees_topdown() if str(c.data) == 'new_line_or_comment'],
            'traversals': [content(c, source) for c in tree.iter_subtrees_topdown()
                           if str(c.data) == 'get_attr_expr_term'],
            'functions': [content(children(c, 'identifier')[0], source)
                          for c in tree.iter_subtrees_topdown()
                          if str(c.data) == 'function_call' and children(c, 'identifier')]}


if __name__ == '__main__':
    try:
        if os.name == 'posix':
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
            if sys.platform == 'linux':
                resource.setrlimit(resource.RLIMIT_AS, (1_000_000_000, 1_000_000_000))
        raw = sys.stdin.buffer.read(16_000_001)
        if len(raw) > 16_000_000:
            raise ValueError('Parser input bounds exceeded')
        files = json.loads(raw)
        results = {path: parse(source) for path, source in files.items()}
        json.dump(results, sys.stdout, allow_nan=False)
    except Exception:
        # Parser exception excerpts may contain source secrets: never return them.
        sys.stderr.write('HCL parse failed or exceeds supported bounds')
        sys.exit(2)
