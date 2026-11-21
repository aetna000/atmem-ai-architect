import {validateBlockSpecs} from './block-spec.mjs';

export function preferredNestedScope(project){
  const roots=project.nodes.filter(node=>node.data.kind!=='note'&&!node.data.parentBlockId);
  return roots.length===1&&project.nodes.some(node=>node.data.parentBlockId===roots[0].id)?roots[0].id:null;
}

// Collapse only presentation. Original components, contracts and evidence stay intact.
export function nestedCanvas(project, scope = null) {
  validateBlockSpecs(project.nodes);
  const byId=new Map(project.nodes.map(node=>[node.id,node]));
  for(const edge of project.edges)if(!byId.has(edge.source)||!byId.has(edge.target))throw Error('An interface endpoint does not exist.');
  if(scope==='*'||!project.nodes.some(node=>node.data.parentBlockId))return {...project,projected:false};
  if(scope&&!byId.has(scope))scope=null;
  const children=project.nodes.filter(node=>(node.data.parentBlockId||null)===scope);
  const visible=new Set(children.map(node=>node.id));
  // The enclosing block represents crossings of this subsystem's boundary.
  if(scope)visible.add(scope);
  function owner(id) {
    let node=byId.get(id);
    while(node){
      if(visible.has(node.id))return node.id;
      node=byId.get(node.data.parentBlockId);
    }
    return scope;
  }
  const wires=new Map();
  for(const edge of project.edges){
    const source=owner(edge.source),target=owner(edge.target);
    if(!source||!target||source===target)continue;
    const key=JSON.stringify([source,target]);
    if(!wires.has(key))wires.set(key,{source,target,originals:[]});
    wires.get(key).originals.push(edge);
  }
  if(scope&&![...wires.values()].some(edge=>edge.source===scope||edge.target===scope))visible.delete(scope);
  return {
    projected:true,scope,
    nodes:project.nodes.filter(node=>visible.has(node.id)),
    edges:[...wires.values()].map(({source,target,originals},index)=>({
      id:'nested-wire-'+index,source,target,type:'smoothstep',
      label:originals.length===1?originals[0].label:`${originals.length} interfaces`,
      data:{sourceEdgeIds:originals.map(edge=>edge.id)},
    })),
  };
}
