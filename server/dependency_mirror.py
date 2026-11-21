"""Explicit public dependency artifacts, hashed without importing their code.

No resolver, installer, URL fetch, account discovery or model-selected host path.
The operator registers the directory/read boundary; generated projects own their
dependency choices, portable builds and target qualification.
"""
import hashlib,json,os,re,stat
from pathlib import Path
from urllib.parse import urlsplit


def _read(path,limit):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>limit:raise ValueError('Dependency mirror requires bounded unlinked regular files')
        with os.fdopen(fd,'rb',closefd=False)as stream:
            value=stream.read(limit+1)
        if len(value)>limit:raise ValueError('Dependency mirror file exceeds its bound')
        return value
    finally:os.close(fd)


def inspect_mirror(directory):
    root=Path(directory)
    if root.is_symlink() or not root.is_dir():raise ValueError('Use an operator-owned dependency mirror directory')
    content=_read(root/'index.json',128000);index=json.loads(content)
    if not isinstance(index,dict) or set(index)!={'format','version','artifacts'} or index['format']!='atmem.public-dependency-mirror' or type(index['version']) is not int or index['version']!=1 or not isinstance(index['artifacts'],list) or not 1<=len(index['artifacts'])<=64:raise ValueError('Unrecognized dependency catalog')
    names=set();total=0
    def text(value,limit=200):return isinstance(value,str) and bool(value) and len(value)<=limit and not any(ord(c)<32 for c in value)
    for artifact in index['artifacts']:
        if not isinstance(artifact,dict) or set(artifact)!={'file','sha256','bytes','name','version','kind','license','source','requiresPython','requiresDist'}:raise ValueError('Register complete bounded dependency metadata')
        name=artifact['file']
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+-]{0,199}',name) or name=='index.json' or name in names:raise ValueError('Use unique flat dependency filenames')
        names.add(name)
        if not isinstance(artifact['sha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',artifact['sha256']) or type(artifact['bytes']) is not int or not 0<artifact['bytes']<=32000000:raise ValueError('Dependency artifacts require bounded exact byte/digest pins')
        for key in ['name','version','kind','license']:
            if not text(artifact[key]):raise ValueError('Invalid dependency metadata')
        if artifact['requiresPython'] is not None and not text(artifact['requiresPython']):raise ValueError('Invalid Python applicability')
        if not isinstance(artifact['requiresDist'],list) or len(artifact['requiresDist'])>64 or any(not text(item,500) for item in artifact['requiresDist']):raise ValueError('Bound dependency requirements without truncation')
        source=artifact['source']
        if not isinstance(source,dict) or set(source)!={'url','metadataUrl','metadataSha256','retrievedAt'} or not isinstance(source['metadataSha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',source['metadataSha256']):raise ValueError('Dependency source provenance is required')
        from datetime import datetime
        if not isinstance(source['retrievedAt'],str) or datetime.fromisoformat(source['retrievedAt']).tzinfo is None:raise ValueError('Source observation requires a timezone')
        for key in ['url','metadataUrl']:
            if not text(source[key],2000):raise ValueError('Invalid public dependency source URL')
            url=urlsplit(source[key])
            if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:raise ValueError('Public source metadata cannot contain credentials, queries or fragments')
        data=_read(root/name,32000000)
        if len(data)!=artifact['bytes'] or hashlib.sha256(data).hexdigest()!=artifact['sha256']:raise ValueError('Dependency artifact differs from its registered bytes')
        total+=len(data)
        if total>64000000:raise ValueError('Dependency mirror exceeds its explicit total bound')
    if set(os.listdir(root))!={'index.json',*names}:raise ValueError('Dependency mirror exposes undeclared entries')
    return {'content':content,'sha256':hashlib.sha256(content).hexdigest(),'artifacts':len(names),'bytes':total}
