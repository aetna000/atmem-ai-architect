#!/usr/bin/env python3
"""Operator CLI for one cached-image check; no recipe selection or source repair."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec


def main(args):
    args.output.mkdir(parents=True,exist_ok=False)
    files={}
    data=io.BytesIO()
    if args.source:
        entries=sorted(args.source.rglob('*'))
        if any(p.is_symlink() for p in entries):raise ValueError('Source links are unsupported')
        with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as archive:
            for path in entries:
                if path.is_file():
                    content=path.read_bytes();relative=str(path.relative_to(args.source))
                    files[relative]=hashlib.sha256(content).hexdigest()
                    archive.writestr(relative,content)
        content=data.getvalue()
    else:
        content=args.artifact.read_bytes()
    if args.expected_manifest:
        expected=json.loads(args.expected_manifest.read_text())['files']
        if files!=expected:raise ValueError('Source no longer matches the original generation manifest')
    digest=hashlib.sha256(content).hexdigest()
    if args.digest and args.digest!=digest:raise ValueError('Artifact digest mismatch')
    spec=ValidationSpec(args.name,args.image,tuple(args.command),timeout_seconds=args.seconds)
    worker=DockerValidationWorker(args.endpoint)
    receipt=worker.run(content,digest,spec)
    receipt['inputSourceHashes']=files
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({key:receipt[key] for key in ['validator','artifactSha256','status','exitCode','skipped','output']},indent=2),flush=True)
    if receipt['status']!='passed':raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--source',type=Path)
    source.add_argument('--artifact',type=Path)
    parser.add_argument('--expected-manifest',type=Path)
    parser.add_argument('--digest')
    parser.add_argument('--endpoint',required=True)
    parser.add_argument('--image',required=True)
    parser.add_argument('--name',required=True)
    parser.add_argument('--seconds',type=int,default=60)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if args.command and args.command[0]=='--':args.command=args.command[1:]
    main(args)
