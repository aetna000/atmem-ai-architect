"""Canonical Git object identities, independently checked before any ref write."""
from datetime import datetime, timezone
import hashlib

from .github_adapter import COMMIT
from .inventory import safe_path


def object_sha(kind, raw):
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def tree_sha(entries, changes=None):
    """Reconstruct a complete recursive SHA-1 Git tree; never execute checkout hooks."""
    if len(entries) > 20000:
        raise ValueError('Git tree exceeds its explicit entry bound')
    leaves = {}
    seen = set()
    for item in entries:
        path = safe_path(item['path'])
        if path in seen:
            raise ValueError('Duplicate Git tree entry')
        seen.add(path)
        if item['type'] == 'tree':
            continue
        if item['mode'] not in {'100644', '100755', '120000', '160000'} or not COMMIT.fullmatch(item['sha']):
            raise ValueError('Unsupported Git object identity')
        leaves[path] = (item['mode'], item['sha'])
    for path, value in (changes or {}).items():
        safe_path(path)
        if value is None:
            leaves.pop(path, None)
        else:
            mode, sha = value
            if mode not in {'100644', '100755'} or not COMMIT.fullmatch(sha):
                raise ValueError('Unsupported proposed Git file mode')
            leaves[path] = value
    hierarchy = {}
    for path, value in leaves.items():
        parts = path.split('/')
        current = hierarchy
        for parent in parts[:-1]:
            node = current.setdefault(parent, {})
            if not isinstance(node, dict):
                raise ValueError('Git file/directory collision')
            current = node
        if parts[-1] in current:
            raise ValueError('Git file/directory collision')
        current[parts[-1]] = value
    def encode(node):
        records = []
        for name, value in node.items():
            directory = isinstance(value, dict)
            mode, sha = ('40000', encode(value)) if directory else value
            records.append(((name + ('/' if directory else '')).encode('utf-8'),
                            mode.encode() + b' ' + name.encode('utf-8') + b'\0' + bytes.fromhex(sha)))
        raw = b''.join(record for _, record in sorted(records))
        return object_sha('tree', raw)
    return encode(hierarchy)


def commit_object(tree, parent, message, timestamp):
    if not COMMIT.fullmatch(tree) or not COMMIT.fullmatch(parent) or type(timestamp) is not int or timestamp < 1:
        raise ValueError('Exact tree, parent and timestamp are required')
    if not isinstance(message, str) or not message.endswith('\n') or '\0' in message or len(message) > 2000:
        raise ValueError('Use a bounded canonical commit message')
    identity = 'AtMem AI Architect <architect@atmem.ai> ' + str(timestamp) + ' +0000'
    raw = ('tree ' + tree + '\nparent ' + parent + '\nauthor ' + identity + '\ncommitter ' + identity + '\n\n' + message).encode()
    date = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    author = {'name': 'AtMem AI Architect', 'email': 'architect@atmem.ai', 'date': date}
    return object_sha('commit', raw), {'tree': tree, 'parents': [parent], 'message': message, 'author': author, 'committer': dict(author)}
