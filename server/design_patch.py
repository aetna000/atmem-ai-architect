"""Atomic, revision-bound model edits. No arbitrary JSON paths or requirements rewrite."""
from .contracts import Project,Proposal

def apply_design_patch(project,patch):
    if patch.baseRevision!=project.revision:raise ValueError('Compact patch targets the wrong revision')
    result=project.model_dump(exclude_none=True)
    if patch.projectName is not None:result['name']=patch.projectName
    nodes={n['id']:n for n in result['nodes']};edges={e['id']:e for e in result['edges']}
    def remove(records,ids):
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate compact removal')
        for id in ids:
            if id not in records:raise ValueError('Compact removal targets an unknown ID: '+id)
            del records[id]
    remove(edges,patch.removeEdgeIds);remove(nodes,patch.removeNodeIds)
    for node in patch.addNodes:
        if node.id in nodes:raise ValueError('Compact add must not overwrite an existing component: '+node.id)
        nodes[node.id]=node.model_dump(exclude_none=True)
    for edge in patch.addEdges:
        if edge.id in edges:raise ValueError('Compact add must not overwrite an existing connection: '+edge.id)
        edges[edge.id]=edge.model_dump(exclude_none=True)
    touched=set()
    for update in patch.nodeUpdates:
        if update.id not in nodes:raise ValueError('Compact update targets an unknown component: '+update.id)
        key=('node',update.id,update.field)
        if key in touched:raise ValueError('Duplicate compact field update')
        touched.add(key);data=nodes[update.id]['data']
        path=update.field.split('.')
        if path[0]=='config':data=data.setdefault('config',{});field=path[1]
        else:field=path[0]
        value=update.value.model_dump(exclude_none=True) if hasattr(update.value,'model_dump') else update.value
        if value is None:data.pop(field,None)
        else:data[field]=value
    for update in patch.edgeUpdates:
        if update.id not in edges:raise ValueError('Compact update targets an unknown connection: '+update.id)
        key=('edge',update.id,update.field)
        if key in touched:raise ValueError('Duplicate compact field update')
        touched.add(key)
        if update.value is None:edges[update.id].pop(update.field,None)
        else:edges[update.id][update.field]=update.value
    result['nodes']=list(nodes.values());result['edges']=list(edges.values())
    # Revalidate the whole candidate after all edits. Source project is never mutated.
    candidate=Project.model_validate(result)
    return Proposal(baseRevision=project.revision,title=patch.title,body=patch.body,next=candidate)
