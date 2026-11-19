"""Acknowledge exact server-reconciled, proposed file mappings as derived data.

Never erase arbitrary work state, accepted records, source edits or review history.
Snapshot values are checked against the raw submitted design, not a lossy importer.
This establishes context currency only, never code correctness or execution.
"""
import copy
from datetime import datetime
import hashlib
import json
import re

EMPTY={'version':2,'records':[],'intents':[],'snapshots':[],'bindings':[],'history':[],'artifactMappings':[]}
FIELDS={'id','receiptSha256','sessionId','runId','artifactId','artifactSha256','proposalSha256','contextId','contextRevision','contextSha256','definitionSha256','records','files','sourceSnapshotIds','recordedAt','scope'}
VISUAL={'id','type','sourceHandle','targetHandle','style','markerStart','markerEnd','animated','selected','hidden','labelStyle','labelBgStyle','labelBgPadding','labelBgBorderRadius'}


def same_json(first,second):
    # JSON booleans and numbers have distinct meaning (Python True == 1).
    canonical=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    return canonical(first)==canonical(second)


def _sources(file,work,excluded):
    """Raw value identities; dependency edges remain proposed metadata."""
    design=file.get('design',{});discovery=file.get('discovery',{});extensions=file.get('extensions',{})
    values={'project:identity':('identity',{'id':file['meta']['id']}),'selection:provider':('selection',{'provider':design.get('provider')or'tools'})}
    intent={'text':discovery.get('problem')or''}
    for key in ['brief','useCases','facts','workflow']:
        if key in discovery:intent[key]=discovery[key]
    if file['meta'].get('domain'):intent['domain']=file['meta']['domain']
    notes=[]
    for node in design.get('nodes',[]):
        if node['data'].get('kind')=='note':
            data={k:v for k,v in node['data'].items()if k not in {'inputPosition','outputPosition','config','provider','origin'}}
            notes.append({'id':node['id'],'data':{'description':'',**data}})
        else:values['block:'+node['id']]=('responsibility',{k:v for k,v in node['data'].items()if k not in {'inputPosition','outputPosition'}})
    if notes:intent['annotations']=sorted(notes,key=lambda row:row['id'].encode('utf-16-be'))
    if extensions.get('terraformState')is not None and 'terraformState'in extensions:intent['terraformState']=extensions['terraformState']
    values['intent:project']=('intent',intent)
    for field,prefix,kind in [('requirements','requirement','requirement'),('assumptions','assumption','assumption'),('openQuestions','question','question'),('decisions','decision','decision')]:
        for row in file.get(field,[]):values[prefix+':'+row['id']]=(kind,row)
    for row in work['intents']:values['intent:'+row['id']]=('intent',row)
    for row in work['records']:
        if row['id']not in excluded:values['work:'+row['id']]=(row['kind'],row)
    for edge in design.get('edges',[]):values['interface:'+edge['id']]=('interface',{k:v for k,v in edge.items()if k not in VISUAL})
    return values


def acknowledged_mapping(store,scope,session,manifest,submitted,current):
    """Acknowledge a bounded chain of exact receipts, never arbitrary work edits."""
    try:
        store.get(scope,session)
        old=submitted.get('extensions',{}).get('architectureWork',EMPTY)
        work=current.get('extensions',{}).get('architectureWork')
        if not isinstance(work,dict)or set(work)!=set(EMPTY)or work['version']!=2 or old.get('version')!=2:return None
        if any(not isinstance(work[key],list)for key in EMPTY if key!='version'):return None
        if not same_json(work['bindings'],old['bindings'])or not same_json(work['history'],old['history']):return None
        prior=old['artifactMappings'];mappings=work['artifactMappings']
        if not len(prior)<len(mappings)<=1000 or not same_json(mappings[:len(prior)],prior):return None
        latest=mappings[-1]
        if latest['sessionId']!=session or latest['artifactId']!=manifest['id']or latest['artifactSha256']!=manifest['sha256']or latest['runId']!=manifest['runId']:return None
        snapshots=work['snapshots'];before=old['snapshots']
        if len(snapshots)>4000 or len(snapshots)<len(before)or not same_json(snapshots[:len(before)],before):return None
        by_id={snapshot['id']:snapshot for snapshot in snapshots}
        if len(by_id)!=len(snapshots):return None
        next_id=1+max([int(snapshot['id'][6:])for snapshot in before if re.fullmatch(r'basis-\d+',snapshot['id'])]+[0])
        new=snapshots[len(before):]
        if [snapshot['id']for snapshot in new]!=['basis-'+str(next_id+i)for i in range(len(new))]:return None
        merged={record['id']:record for record in old['records']};previous_mappings=list(prior)
        added_ids=set();referenced=set()
        from .engineering_handoff import design_value
        for mapping in mappings[len(prior):]:
            if set(mapping)!=FIELDS or mapping['scope']!='artifact_file_binding_only'or mapping['sessionId']!=session:return None
            row=store.db.execute('SELECT sha256,payload FROM engineering_reconciliations WHERE id=? AND session=? AND artifact=?',(mapping['id'],session,mapping['artifactId'])).fetchone()
            if row is None or row['sha256']!=mapping['receiptSha256']or hashlib.sha256(row['payload'].encode()).hexdigest()!=row['sha256']:return None
            payload=json.loads(row['payload']);context=payload['context']
            if payload['projectId']!=scope.project or payload['sessionId']!=session:return None
            if payload['boundary']!='artifact_file_binding_only'or payload['format']!='atmem.architecture-proposal'or type(payload['version'])is not int or payload['version']!=1:return None
            if not same_json(design_value(context['content'].encode(),scope.project),submitted):return None
            if hashlib.sha256(context['content'].encode()).hexdigest()!=context['sha256']:return None
            expected_fields={key:payload[key]for key in ['artifactId','artifactSha256','runId','proposalSha256','definitionSha256','files']}
            expected_fields.update(contextId=context['id'],contextRevision=context['revision'],contextSha256=context['sha256'])
            if any(not same_json(mapping[key],expected)for key,expected in expected_fields.items()):return None
            if not isinstance(mapping['recordedAt'],str)or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z',mapping['recordedAt']):return None
            datetime.fromisoformat(mapping['recordedAt'].replace('Z','+00:00'))
            records=[{**record,'source':'agent','agreement':'proposed'}for record in payload['proposal']['records']]
            if not records or not same_json(mapping['records'],records):return None
            ids={record['id']for record in records}
            # Same-context repairs must retain previous proposed identities.
            # A new client context can explicitly include/reconcile older mappings.
            if len(ids)!=len(records)or not added_ids<=ids:return None
            for record in records:
                previous=merged.get(record['id'])
                if previous:
                    binding=next((item for item in reversed(previous_mappings)if any(r['id']==record['id']for r in item['records'])),None)
                    if not binding or binding['sessionId']!=session or previous.get('source')!='agent'or previous.get('agreement')!='proposed'or not same_json(previous,next(r for r in binding['records']if r['id']==record['id'])):return None
                merged[record['id']]=record
            references=mapping['sourceSnapshotIds']
            if not isinstance(references,list)or len(references)>4000 or len(set(references))!=len(references)or any(id not in by_id for id in references):return None
            raw=json.loads(context['content']);expected=_sources(raw,{**old,'intents':work['intents']},ids)
            selected=[by_id[id]for id in references]
            if len(selected)!=len(expected)or {snapshot['ref']for snapshot in selected}!=set(expected):return None
            known=set(expected)|{'work:'+id for id in ids}
            for snapshot in selected:
                if set(snapshot)!={'id','ref','value'}or set(snapshot['value'])!={'id','kind','title','value','dependsOn'}:return None
                value=snapshot['value'];ref=snapshot['ref'];kind,meaning=expected[ref]
                if value['id']!=ref or value['kind']!=kind or not isinstance(value['title'],str):return None
                observed=value['value']
                if ref.startswith('block:')and isinstance(observed,dict):observed={key:value for key,value in observed.items()if key!='externalProvenance'}
                if not same_json(observed,meaning):return None
                dependencies=value['dependsOn']
                if not isinstance(dependencies,list)or len(set(dependencies))!=len(dependencies)or any(dep not in known for dep in dependencies):return None
            added_ids|=ids;referenced.update(references);previous_mappings.append(mapping)
        if not same_json(work['records'],list(merged.values()))or any(snapshot['id']not in referenced for snapshot in new):return None
        projected=copy.deepcopy(current);projected['extensions']['architectureWork']={**copy.deepcopy(old),'intents':copy.deepcopy(work['intents'])}
        return projected
    except (KeyError,TypeError,ValueError,StopIteration):
        return None
