"""Normalized source snapshot contract; vendor permission mapping is separately verified.

Local contract fixtures do not establish SharePoint or Confluence compatibility.
A complete snapshot carries explicit resolved subject/region ACLs for every item.
"""
import hashlib
import json
import time
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit
from catalog_admin import validate_document

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        raise ValueError('Source redirects are not allowed')


def fetch_snapshot(endpoint,token=None,allow_local_fixture=False):
    url=urlsplit(endpoint)
    local=url.hostname in {'127.0.0.1','localhost','::1'}
    if url.username or url.password or url.fragment or url.query:raise ValueError('Use a credential-free source endpoint')
    if url.scheme!='https' and not (allow_local_fixture and local and url.scheme=='http'):raise ValueError('HTTPS is required outside an explicit loopback fixture')
    headers={'Accept':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    with build_opener(NoRedirect).open(Request(endpoint,headers=headers),timeout=10) as response:
        raw=response.read(1_000_001)
    if len(raw)>1_000_000:raise ValueError('Source snapshot exceeds the bounded contract')
    value=json.loads(raw)
    if not isinstance(value,dict) or value.get('complete') is not True or value.get('permissionsComplete') is not True:raise ValueError('Incomplete source data or permissions; do not publish a partial snapshot')
    if not isinstance(value.get('snapshotId'),str) or not value['snapshotId'] or not isinstance(value.get('documents'),list) or len(value['documents'])>100:raise ValueError('Invalid bounded source snapshot')
    return value


def normalized_documents(snapshot,source_id,lease_seconds=60):
    if not isinstance(lease_seconds,int) or not 1<=lease_seconds<=300:raise ValueError('Authorization freshness must be 1–300 seconds')
    if not isinstance(snapshot,dict) or snapshot.get('complete') is not True or snapshot.get('permissionsComplete') is not True or not isinstance(snapshot.get('documents'),list) or len(snapshot['documents'])>100:raise ValueError('Incomplete bounded snapshot')
    result={};expiry=int(time.time())+lease_seconds
    for entry in snapshot['documents']:
        if not isinstance(entry,dict) or not isinstance(entry.get('sourceId'),str) or not isinstance(entry.get('sourceVersion'),str) or not entry.get('sourceId') or not entry.get('sourceVersion'):raise ValueError('Exact source identity and version are required')
        identity=hashlib.sha256(json.dumps([source_id,entry['sourceId']],separators=(',',':')).encode()).hexdigest()
        if identity in result:raise ValueError('Duplicate source identity')
        doc={'id':identity,'title':entry.get('title'),'text':entry.get('text'),'allowedSubjects':entry.get('allowedSubjects'),'allowedRegions':entry.get('allowedRegions'),'sourceId':source_id,'authorizationExpiresAt':expiry}
        result[identity]={'document':validate_document(doc),'sourceVersion':entry['sourceVersion']}
    return result


def synchronize(snapshot,source_id,store,checkpoint,lease_seconds=60):
    """Conditional, retryable writes; checkpoint only after a complete reconciliation.

    The store is a source-scoped adapter with get/put/delete; each mutation checks
    the current revision. Failed syncs never renew missing documents' leases.
    """
    desired=normalized_documents(snapshot,source_id,lease_seconds)
    previous=checkpoint.load(source_id) or {'documents':{}}
    inventory=set(previous['documents'])|set(previous.get('pending',[]))
    checkpoint.save(source_id,{**previous,'pending':sorted(inventory|set(desired))})
    completed={}
    for identity,entry in desired.items():
        current=store.get(identity)
        if current and current.get('sourceId')!=source_id:raise ValueError('Source ownership mismatch')
        saved=store.put(entry['document'],current.get('revision') if current else None)
        completed[identity]={'revision':saved['revision'],'sourceVersion':entry['sourceVersion']}
    for identity in inventory-set(desired):
        current=store.get(identity)
        if current:
            if current.get('sourceId')!=source_id:raise ValueError('Source ownership mismatch')
            store.delete(identity,current['revision'])
    result={'snapshotId':snapshot['snapshotId'],'documents':completed}
    checkpoint.save(source_id,result)
    return {'status':'synchronized','documents':len(completed),'authorizationLeaseSeconds':lease_seconds}
