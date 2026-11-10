"""Trusted ECS byte-transfer stages; never parse a document in this image."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from enterprise_aws_jobs import transfer_metadata
from enterprise_aws_objects import S3DocumentObjects
from enterprise_document_contract import MAX_INPUT
from enterprise_document_job import MAX_ENVELOPE,read_file,request,result,unique


def metadata(encoded):
    if not isinstance(encoded,str)or not 0<len(encoded.encode())<=4096:raise ValueError('Invalid transfer metadata')
    value=json.loads(encoded,object_pairs_hook=unique)
    fields={'format','accountId','region','bucket','request','inputETag'}
    if not isinstance(value,dict)or set(value)!=fields or value['format']!='enterprise-aws-document-transfer-v1':raise ValueError('Invalid transfer metadata')
    # Validate the fixed destination without constructing a native SDK client.
    S3DocumentObjects(value['bucket'],value['region'],value['accountId'])
    if transfer_metadata(value,value['request'],value['inputETag'])!=value:raise ValueError('Invalid transfer metadata')
    return value


def directories(mount):
    root=source=target=None
    try:
        root=os.open(mount,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        source=os.open('input',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root)
        target=os.open('output',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root)
        left,right=os.fstat(source),os.fstat(target)
        if (left.st_dev,left.st_ino)==(right.st_dev,right.st_ino):raise ValueError('Use distinct per-file mounts')
        return source,target
    except BaseException:
        for fd in (target,source):
            if fd is not None:os.close(fd)
        raise
    finally:
        if root is not None:os.close(root)


def download(value,objects,mount='/work'):
    source,target=directories(mount)
    try:
        # ECS mounts fresh task-local volumes before this stage starts. Existing
        # content, including partial files, must never be adopted for another job.
        if os.listdir(source)or os.listdir(target):raise ValueError('Use fresh per-file mounts')
        expected=value['request'];identifier=expected['requestId']
        raw=objects.load(identifier,'input',value['inputETag'])
        if request(raw,expected['mediaType'],identifier)!=expected:raise ValueError('Input binding changed')
        for name,content in [('document',raw),('request.json',json.dumps(expected,separators=(',',':')).encode())]:
            fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400,dir_fd=source)
            with os.fdopen(fd,'wb')as stream:
                stream.write(content);stream.flush();os.fsync(stream.fileno());os.fchown(stream.fileno(),10001,10001)
        os.fchmod(source,0o500);os.fchmod(target,0o700)
        os.fchown(source,10001,10001);os.fchown(target,10001,10001)
        os.fsync(source);os.fsync(target)
    finally:os.close(target);os.close(source)


def upload(value,objects,mount='/work'):
    source,target=directories(mount)
    try:
        expected=value['request'];identifier=expected['requestId']
        raw=read_file(source,'document',MAX_INPUT)
        if request(raw,expected['mediaType'],identifier)!=expected:raise ValueError('Input binding changed')
        encoded=read_file(target,'result.json',MAX_ENVELOPE)
        result(raw,expected['mediaType'],identifier,encoded)
        objects.put(identifier,'result',encoded)
    finally:os.close(target);os.close(source)


def main():
    try:
        if sys.argv[1:]not in [['download'],['upload']]:raise ValueError()
        mode=sys.argv[1]
        if os.getuid()!=(0 if mode=='download'else 10001):raise ValueError()
        value=metadata(os.environ['DOCUMENT_JOB'])
        objects=S3DocumentObjects(value['bucket'],value['region'],value['accountId'])
        (download if mode=='download'else upload)(value,objects)
    except Exception:raise SystemExit(2)from None


if __name__=='__main__':main()
