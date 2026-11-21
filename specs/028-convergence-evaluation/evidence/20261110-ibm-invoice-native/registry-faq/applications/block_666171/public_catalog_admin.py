"""Operator-only public article lifecycle; no anonymous write endpoint.

The cloud service authorizes each read/write using its native IAM. Local flags are
an intent guard, never a replacement for the emitted editor-role policy.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid
from public_catalog_store import HttpCatalogStore,S3CatalogStore
from public_faq import MAX_ARTICLES,MAX_ARTICLE_BYTES,CatalogChanged,CatalogUnavailable,parse_catalog

def read_article(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('Choose a regular public text file, not a symlink or directory')
    with path.open('rb') as stream:raw=stream.read(MAX_ARTICLE_BYTES+1)
    if len(raw)>MAX_ARTICLE_BYTES:raise ValueError('Public article exceeds 30000 UTF-8 bytes')
    return raw.decode('utf-8')

def encode_catalog(articles):
    raw=json.dumps({'format':'atmem-public-faq-v1','revision':str(uuid.uuid4()),'articles':articles},ensure_ascii=False,separators=(',',':')).encode()
    try:parse_catalog(raw,'editor-preflight')
    except CatalogUnavailable:raise ValueError('Invalid public article collection') from None
    return raw

def initial_catalog(directory):
    folder=Path(directory)
    if folder.is_symlink() or not folder.is_dir():raise ValueError('Choose a dedicated public article directory')
    paths=sorted(folder.iterdir())
    if not 1<=len(paths)<=MAX_ARTICLES:raise ValueError('Use 1–100 public text/Markdown files')
    articles=[]
    for path in paths:
        if path.suffix.lower() not in {'.txt','.md'}:raise ValueError('Every entry must be a public UTF-8 .txt or .md file; nothing is silently skipped')
        slug=re.sub(r'[^a-z0-9_.-]+','-',path.stem.casefold()).strip('-_.')[:80] or 'public-article'
        identifier=slug+'-'+hashlib.sha256(path.name.encode('utf-8')).hexdigest()[:16]
        articles.append({'id':identifier,'revision':str(uuid.uuid4()),'title':path.stem.replace('-',' ').replace('_',' ').strip(),'text':read_article(path),'url':'','visibility':'public'})
    return encode_catalog(articles)

def expected_version(provider,value):
    if value=='create':return '0' if provider=='gcp' else None
    if not isinstance(value,str) or not value:raise ValueError('Supply the exact observed storage version')
    return value

def edit_catalog(current,operation,*,article_id,title=None,file=None,url=''):
    articles=[{'id':a.id,'revision':a.revision,'title':a.title,'text':a.text,'url':a.url,'visibility':'public'} for a in current.articles]
    matches=[i for i,a in enumerate(articles) if a['id']==article_id]
    if operation=='delete':
        if not matches:raise ValueError('Article does not exist')
        del articles[matches[0]]
    elif operation=='upsert':
        new={'id':article_id,'revision':str(uuid.uuid4()),'title':title,'text':read_article(file),'url':url,'visibility':'public'}
        if matches:articles[matches[0]]=new
        else:articles.append(new)
    else:raise ValueError('Unsupported catalog edit')
    return encode_catalog(articles)

def token_headers(path):
    file=Path(path)
    if file.is_symlink() or not file.is_file():raise PermissionError('Use a private regular token file')
    metadata=file.stat()
    if stat.S_IMODE(metadata.st_mode)&0o077 or hasattr(os,'getuid') and metadata.st_uid!=os.getuid():raise PermissionError('Token file must belong to the operator with no group/other access')
    with file.open('r',encoding='utf-8') as stream:token=stream.read(16385).strip()
    if not token or len(token)>16384 or any(c.isspace() for c in token):raise PermissionError('Invalid short-lived editor token')
    return {'Authorization':'Bearer '+token}

def build_store(args):
    if args.provider=='aws':
        if args.token_file:raise ValueError('AWS uses the approved role credential chain, not a user bearer token')
        return S3CatalogStore(args.bucket,args.region,args.aws_account_id)
    if not args.token_file:raise ValueError('Supply a private file containing the approved short-lived editor access token')
    return HttpCatalogStore(args.provider,args.region,args.bucket,lambda:token_headers(args.token_file),account=args.azure_account)

def operate(args,store):
    if args.operation=='inspect':
        current=store.load()
        return {'catalogRevision':current.revision,'storageVersion':current.version,'articles':[{'id':a.id,'revision':a.revision,'title':a.title} for a in current.articles]}
    if not args.confirm_write:raise PermissionError('A catalog write requires explicit operator intent')
    expected=expected_version(args.provider,args.expected_version)
    if args.operation=='init':
        if args.expected_version!='create':raise ValueError('Initialization must require an absent catalog')
        raw=initial_catalog(args.directory)
    else:
        if args.expected_version=='create':raise ValueError('Inspect the current catalog before editing it')
        current=store.load()
        if current.version!=expected:raise CatalogChanged('Catalog changed; review the current version')
        raw=edit_catalog(current,args.operation,article_id=args.id,title=args.title,file=args.file,url=args.url)
    version=store.save(raw,expected);saved=parse_catalog(raw,version)
    return {'catalogRevision':saved.revision,'storageVersion':version,'articleCount':len(saved.articles)}

def parser():
    p=argparse.ArgumentParser(description='Manage only the dedicated public FAQ catalog with an approved editor identity.')
    p.add_argument('--provider',choices=['aws','azure','gcp','ibm'],required=True);p.add_argument('--bucket',required=True);p.add_argument('--region',required=True)
    p.add_argument('--aws-account-id');p.add_argument('--azure-account');p.add_argument('--token-file',help='Private file containing an approved short-lived storage token; never a browser user token or API key')
    commands=p.add_subparsers(dest='operation',required=True)
    commands.add_parser('inspect')
    for command in ['init','upsert','delete']:
        sub=commands.add_parser(command);sub.add_argument('--confirm-write',action='store_true');sub.add_argument('--expected-version',required=True,help='Exact version from inspect; use create only for initialization')
        if command=='init':sub.add_argument('--directory',required=True)
        else:
            sub.add_argument('--id',required=True);sub.set_defaults(title=None,file=None,url='')
            if command=='upsert':sub.add_argument('--title',required=True);sub.add_argument('--file',required=True);sub.add_argument('--url',default='')
    return p

def main():
    args=parser().parse_args()
    try:result=operate(args,build_store(args))
    except CatalogChanged:
        print('Catalog changed. Inspect the latest version, review the edit and retry explicitly.',file=sys.stderr);return 2
    except PermissionError:
        print('Access denied or editor intent is missing. Use the approved catalog editor role and a private short-lived token file where required.',file=sys.stderr);return 3
    except (ValueError,UnicodeError,OSError):
        print('Invalid public catalog input or destination. Check the command and text-file limits; no successful write is confirmed.',file=sys.stderr);return 4
    except Exception:
        print('Storage outcome could not be confirmed. Inspect the current catalog version before retrying; no automatic retry was performed.',file=sys.stderr);return 5
    print(json.dumps(result,ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
