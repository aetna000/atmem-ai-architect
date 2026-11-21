// Shared language-neutral model. Diagram placements reference semantic elements.
// This first grammar covers classifiers and relational data; behavior/infra follow.
const kinds=new Set(['package','class','interface','dataType','enumeration','entity','table']);
const relationshipKinds=new Set(['association','aggregation','composition','generalization','realization','dependency','foreignKey','mapping']);
const classifierKinds=new Set(['class','interface','dataType','enumeration']);
const text=(v,max=4000)=>typeof v==='string'&&v.trim().length>0&&Array.from(v).length<=max;
const object=v=>v&&typeof v==='object'&&!Array.isArray(v);
const fail=message=>{throw Error('Engineering model: '+message);};
function fields(value,allowed,required,label){if(!object(value)||Object.keys(value).some(k=>!allowed.includes(k))||required.some(k=>!Object.hasOwn(value,k)))fail(label+' has missing or unsupported fields.');}
function list(value,max,label){if(!Array.isArray(value)||value.length>max)fail(label+' exceeds its collection contract.');return value;}
function strings(values,max,label){for(const value of list(values,max,label))if(!text(value))fail(label+' requires populated text.');}
function multiplicity(value,label){fields(value,['lower','upper'],['lower','upper'],label);if(!Number.isSafeInteger(value.lower)||value.lower<0||value.upper!=='*'&&(!Number.isSafeInteger(value.upper)||value.upper<value.lower))fail(label+' has invalid multiplicity.');}
function unique(values,label){if(new Set(values).size!==values.length)fail(label+' contains duplicate references.');}

export function validateEngineeringModel(model,{blockIds,requirementIds}={}){
 if(model==null)return null;
 fields(model,['format','version','id','name','elements','relationships','diagrams'],['format','version','id','name','elements','relationships','diagrams'],'root');
 if(model.format!=='atmem.engineering-model'||model.version!==1||!text(model.id,100)||!text(model.name,200))fail('unsupported model identity or version.');
 const ids=new Set(),all=new Map(),elements=new Map(),relationships=new Map();
 function identity(value,label){if(!text(value.id,100)||ids.has(value.id))fail(label+' requires a globally unique ID.');ids.add(value.id);all.set(value.id,value);if(!text(value.name,200))fail(label+' needs a name.');}
 function typeRef(value,label){if(!text(value,100))fail(label+' needs a logical type reference.');}
 function member(value,label,parameter=false){
  fields(value,['id','name','typeRef','visibility','multiplicity','readOnly','defaultValue','description',...(parameter?['direction']:['nullable'])],['id','name','typeRef'],label);identity(value,label);typeRef(value.typeRef,label);
  if(value.visibility!==undefined&&!['public','protected','private','package'].includes(value.visibility))fail(label+' has invalid visibility.');
  if(value.multiplicity!==undefined)multiplicity(value.multiplicity,label);
  for(const key of ['nullable','readOnly'])if(value[key]!==undefined&&typeof value[key]!=='boolean')fail(label+' has an invalid '+key+'.');
  if(value.description!==undefined&&!text(value.description))fail(label+' has invalid description.');
  if(value.defaultValue!==undefined&&(typeof value.defaultValue!=='string'||Array.from(value.defaultValue).length>4000))fail(label+' has invalid default value.');
  if(parameter&&!['in','out','inout','return'].includes(value.direction))fail(label+' needs an explicit parameter direction.');
 }
 for(const element of list(model.elements,2000,'elements')){
  fields(element,['id','name','kind','ownerId','blockId','description','basis','requirementIds','attributes','operations','invariants','literals','columns','primaryKey','indexes','checks','physicalMapping'],['id','name','kind','basis'],'element');identity(element,'element');
  if(!kinds.has(element.kind)||!['source','proposed','accepted'].includes(element.basis))fail('element kind or design basis is invalid.');elements.set(element.id,element);
  if(element.description!==undefined&&!text(element.description))fail('element description is invalid.');
  for(const key of ['ownerId','blockId'])if(element[key]!==undefined&&!text(element[key],100))fail('invalid '+key+'.');
  if(element.blockId!==undefined&&blockIds&&!blockIds.includes(element.blockId))fail('element refers to an unknown architecture block.');
  if(element.requirementIds!==undefined){strings(element.requirementIds,100,'requirements');unique(element.requirementIds,'requirements');if(requirementIds&&element.requirementIds.some(id=>!requirementIds.includes(id)))fail('element refers to an unknown requirement.');}
  const classifier=classifierKinds.has(element.kind),data=['entity','table'].includes(element.kind);
  for(const key of ['attributes','operations','invariants'])if(element[key]!==undefined&&!classifier)fail(key+' belongs to a classifier.');
  for(const key of ['columns','primaryKey','indexes','checks','physicalMapping'])if(element[key]!==undefined&&!data)fail(key+' belongs to a data entity.');
  if(element.literals!==undefined&&element.kind!=='enumeration')fail('literals belong to an enumeration.');
  if(element.attributes!==undefined)for(const value of list(element.attributes,200,'attributes'))member(value,'attribute');
  if(element.operations!==undefined)for(const operation of list(element.operations,200,'operations')){
   fields(operation,['id','name','visibility','description','parameters','preconditions','postconditions','raises'],['id','name','parameters'],'operation');identity(operation,'operation');
   if(operation.visibility!==undefined&&!['public','protected','private','package'].includes(operation.visibility))fail('invalid operation visibility.');
   if(operation.description!==undefined&&!text(operation.description))fail('invalid operation description.');
   for(const parameter of list(operation.parameters,100,'parameters'))member(parameter,'parameter',true);
   if(operation.parameters.filter(p=>p.direction==='return').length>1)fail('operation has more than one return parameter.');
   for(const key of ['preconditions','postconditions','raises'])if(operation[key]!==undefined)strings(operation[key],100,key);
  }
  if(element.invariants!==undefined)strings(element.invariants,100,'invariants');
  if(element.literals!==undefined){strings(element.literals,100,'literals');unique(element.literals,'literals');}
  if(element.columns!==undefined)for(const column of list(element.columns,300,'columns')){member(column,'column');if(column.visibility!==undefined||column.multiplicity!==undefined||column.readOnly!==undefined)fail('column visibility/multiplicity/readOnly is not a storage constraint.');if(typeof column.nullable!=='boolean')fail('column nullability must be explicit.');}
  const columns=new Set((element.columns||[]).map(c=>c.id));
  if(element.primaryKey!==undefined){strings(element.primaryKey,100,'primary key');unique(element.primaryKey,'primary key');if(!element.primaryKey.length||element.primaryKey.some(id=>!columns.has(id)||(element.columns.find(c=>c.id===id).nullable)))fail('primary key must reference non-nullable columns of its entity.');}
  if(element.indexes!==undefined)for(const index of list(element.indexes,100,'indexes')){fields(index,['id','name','columns','unique','purpose'],['id','name','columns','unique','purpose'],'index');identity(index,'index');strings(index.columns,100,'index columns');unique(index.columns,'index columns');if(!index.columns.length||index.columns.some(id=>!columns.has(id))||typeof index.unique!=='boolean'||!text(index.purpose))fail('index needs owned columns, uniqueness and query purpose.');}
  if(element.checks!==undefined)for(const check of list(element.checks,100,'checks')){fields(check,['id','name','expression','language'],['id','name','expression','language'],'check');identity(check,'check');if(!text(check.expression)||!text(check.language,100))fail('check needs an explicit expression and language.');}
  if(element.physicalMapping!==undefined){fields(element.physicalMapping,['technology','namespace','name','columnTypes'],['technology','name','columnTypes'],'physical mapping');if(!text(element.physicalMapping.technology,150)||!text(element.physicalMapping.name,200)||!object(element.physicalMapping.columnTypes)||Object.entries(element.physicalMapping.columnTypes).some(([id,type])=>!columns.has(id)||!text(type,200)))fail('invalid physical type mapping.');if(element.physicalMapping.namespace!==undefined&&!text(element.physicalMapping.namespace,200))fail('invalid physical namespace.');}
 }
 for(const element of elements.values()){
  const seen=new Set([element.id]);let owner=element.ownerId;
  while(owner!==undefined){if(!elements.has(owner)||seen.has(owner))fail('ownership has an unknown element or cycle.');seen.add(owner);owner=elements.get(owner).ownerId;}
  for(const feature of [...(element.attributes||[]),...(element.columns||[]),...(element.operations||[]).flatMap(op=>op.parameters)])if(!classifierKinds.has(elements.get(feature.typeRef)?.kind))fail('feature '+feature.id+' refers to an unknown logical type.');
  for(const op of element.operations||[])for(const id of op.raises||[])if(!classifierKinds.has(elements.get(id)?.kind))fail('operation exception type is unknown.');
 }
 for(const relation of list(model.relationships,4000,'relationships')){
  fields(relation,['id','name','kind','source','target','sourceEnd','targetEnd','sourceColumns','targetColumns','onDelete','onUpdate','description'],['id','name','kind','source','target'],'relationship');identity(relation,'relationship');
  const source=elements.get(relation.source),target=elements.get(relation.target);
  if(!relationshipKinds.has(relation.kind)||!source||!target)fail('relationship has an unsupported kind or missing endpoint.');
  for(const key of ['sourceEnd','targetEnd'])if(relation[key]!==undefined){fields(relation[key],['role','multiplicity','navigable'],[],'relationship end');if(relation[key].multiplicity)multiplicity(relation[key].multiplicity,'relationship end');if(relation[key].role!==undefined&&!text(relation[key].role,150)||relation[key].navigable!==undefined&&typeof relation[key].navigable!=='boolean')fail('relationship end is invalid.');}
  if(relation.description!==undefined&&!text(relation.description))fail('relationship description is invalid.');
  const fk=relation.kind==='foreignKey';for(const key of ['sourceColumns','targetColumns','onDelete','onUpdate'])if(relation[key]!==undefined&&!fk)fail('foreign-key properties need a foreign-key relationship.');
  if(fk){
   if(!['entity','table'].includes(source.kind)||!['entity','table'].includes(target.kind))fail('foreign key endpoints must be data entities.');
   for(const key of ['sourceColumns','targetColumns']){strings(relation[key],100,key);unique(relation[key],key);}
   if(!relation.sourceColumns.length||relation.sourceColumns.length!==relation.targetColumns.length)fail('foreign key column mappings must have matching arity.');
   relation.sourceColumns.forEach((id,i)=>{const a=source.columns?.find(c=>c.id===id),b=target.columns?.find(c=>c.id===relation.targetColumns[i]);if(!a||!b||a.typeRef!==b.typeRef)fail('foreign key column ownership/type mismatch.');});
   if(![target.primaryKey,...(target.indexes||[]).filter(i=>i.unique).map(i=>i.columns)].some(ids=>JSON.stringify(ids)===JSON.stringify(relation.targetColumns)))fail('foreign key target must match an ordered unique key.');
   for(const key of ['onDelete','onUpdate'])if(relation[key]!==undefined&&!['restrict','noAction','cascade','setNull','setDefault'].includes(relation[key]))fail('invalid referential action.');
   if([relation.onDelete,relation.onUpdate].includes('setNull')&&relation.sourceColumns.some(id=>!source.columns.find(c=>c.id===id).nullable))fail('setNull conflicts with non-nullable foreign key columns.');
  }
  if(relation.kind==='realization'&&(!classifierKinds.has(source.kind)||target.kind!=='interface'))fail('realization must target an interface.');
  if(relation.kind==='generalization'&&(!classifierKinds.has(source.kind)||!classifierKinds.has(target.kind)||source.id===target.id))fail('generalization requires distinct classifiers.');
  if(relation.kind==='mapping'&&(!classifierKinds.has(source.kind)||!['entity','table'].includes(target.kind)))fail('storage mapping must connect a classifier to a data entity.');
  relationships.set(relation.id,relation);
 }
 const inheritance=new Map();for(const r of relationships.values())if(r.kind==='generalization')inheritance.set(r.source,[...(inheritance.get(r.source)||[]),r.target]);
 const resolvedInheritance=new Set();
 function ancestors(id,path=new Set()){if(resolvedInheritance.has(id))return;if(path.has(id))fail('generalization contains a cycle.');const next=new Set(path);next.add(id);for(const parent of inheritance.get(id)||[])ancestors(parent,next);resolvedInheritance.add(id);}
 for(const id of inheritance.keys())ancestors(id);
 for(const diagram of list(model.diagrams,500,'diagrams')){
  fields(diagram,['id','name','kind','scopeId','placements','relationships'],['id','name','kind','placements','relationships'],'diagram');identity(diagram,'diagram');
  if(!['class','schema'].includes(diagram.kind))fail('this model version supports class and schema views only.');
  if(diagram.scopeId!==undefined&&!elements.has(diagram.scopeId))fail('diagram scope does not exist.');
  const visible=new Set();for(const placement of list(diagram.placements,300,'placements')){
   fields(placement,['elementId','x','y','detail'],['elementId','x','y'],'placement');const element=elements.get(placement.elementId);
   if(!element||visible.has(placement.elementId)||!Number.isFinite(placement.x)||!Number.isFinite(placement.y)||Math.abs(placement.x)>1_000_000||Math.abs(placement.y)>1_000_000||placement.detail!==undefined&&!['summary','full'].includes(placement.detail))fail('diagram placement is invalid.');
   if(diagram.kind==='class'&&!classifierKinds.has(element.kind)||diagram.kind==='schema'&&!['entity','table'].includes(element.kind))fail('element kind does not belong in this diagram.');visible.add(placement.elementId);
  }
  strings(diagram.relationships,1000,'diagram relationships');unique(diagram.relationships,'diagram relationships');
  for(const id of diagram.relationships){const r=relationships.get(id);if(!r||!visible.has(r.source)||!visible.has(r.target))fail('diagram relationship must reference visible endpoints.');}
 }
 return model;
}

export function engineeringElementIndex(model){validateEngineeringModel(model);const index=new Map();for(const e of model.elements){index.set(e.id,{element:e,owner:null});for(const member of [...(e.attributes||[]),...(e.columns||[]),...(e.operations||[])]){index.set(member.id,{element:member,owner:e});for(const parameter of member.parameters||[])index.set(parameter.id,{element:parameter,owner:member});}}return index;}
export function engineeringDiagram(model,diagramId){validateEngineeringModel(model);const diagram=model.diagrams.find(d=>d.id===diagramId);if(!diagram)fail('diagram does not exist.');const index=engineeringElementIndex(model);return {...diagram,elements:diagram.placements.map(placement=>({element:index.get(placement.elementId).element,placement})),connectors:diagram.relationships.map(id=>model.relationships.find(r=>r.id===id))};}

const canonical=value=>JSON.stringify(value,(_,v)=>object(v)?Object.fromEntries(Object.keys(v).sort().map(key=>[key,v[key]])):v);
// Generated proposals may refine proposed details, never manufacture approval or
// silently drop existing semantic identities. Explicit removal needs a later API.
export function reconcileEngineeringModel(previous,proposed,context={}){
 if(proposed===undefined)return validateEngineeringModel(previous,context);
 if(proposed===null)fail('a generated proposal cannot clear the engineering model.');
 validateEngineeringModel(proposed,context);
 const oldElements=new Map((previous?.elements||[]).map(e=>[e.id,e]));
 for(const element of proposed.elements){
  const before=oldElements.get(element.id);
  if(element.basis==='accepted'&&before?.basis!=='accepted')fail('generated details cannot claim owner acceptance.');
  if(before?.basis==='accepted'&&canonical(before)!==canonical(element))fail('accepted elements require an explicit reviewed change.');
 }
 if(!previous)return proposed;
 validateEngineeringModel(previous);
 if(previous.id!==proposed.id)fail('a refinement must preserve the model identity.');
 const collect=model=>{
  const records=new Map();
  function visit(value,parent=null){
   if(Array.isArray(value)){for(const row of value)visit(row,parent);return;}
   if(!object(value))return;
   if(typeof value.id==='string'){records.set(value.id,{value,parent});parent=value.id;}
   for(const child of Object.values(value))if(typeof child==='object')visit(child,parent);
  }
  // Diagram placements and their IDs are presentation, not semantic scope.
  visit(model.elements);visit(model.relationships);return records;
 };
 const current=collect(proposed);
 for(const[id,before]of collect(previous)){
  const after=current.get(id);
  if(!after)fail('refinement cannot remove semantic identity '+id+'.');
  if(before.parent!==after.parent||before.value.kind!==after.value.kind)fail('refinement cannot reassign semantic identity '+id+'.');
  if(before.value.blockId!==undefined&&before.value.blockId!==after.value.blockId)fail('refinement cannot silently change element ownership.');
 }
 const accepted=new Set(previous.elements.filter(e=>e.basis==='accepted').map(e=>e.id));
 for(const relation of previous.relationships)if((accepted.has(relation.source)||accepted.has(relation.target))&&canonical(relation)!==canonical(current.get(relation.id).value))fail('relationships of accepted elements require an explicit reviewed change.');
 return proposed;
}
