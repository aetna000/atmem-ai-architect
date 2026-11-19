import test from'node:test';import assert from'node:assert/strict';
import{validateEngineeringModel,engineeringDiagram,engineeringElementIndex}from'../src/engineering-model.mjs';import{libraryEngineeringModel}from'./fixtures/engineering-model.mjs';import{toProjectFile,parseProjectFile}from'../src/project-file.mjs';
test('class attributes, operations, columns and diagrams resolve to one shared model across domain labels',()=>{
 for(const name of ['Library engineering','Instrument maintenance']){const m=libraryEngineeringModel();m.name=name;validateEngineeringModel(m);const a=engineeringDiagram(m,'classes'),b=engineeringDiagram(m,'loan-focus');assert.equal(a.elements[0].element,b.elements[0].element);m.elements.find(e=>e.id==='loan').attributes[0].name='agreementIdentifier';assert.equal(engineeringDiagram(m,'loan-focus').elements[0].element.attributes[0].name,'agreementIdentifier');assert.equal(engineeringElementIndex(m).get('records-book').owner.id,'records');}
});
test('logical models round-trip through normal project files without selecting a language or physical database',()=>{
 const m=libraryEngineeringModel(),project={version:1,revision:1,name:'Library',provider:'tools',nodes:[{id:'loans',type:'resource',position:{x:0,y:0},data:{label:'Loans',kind:'resource',provider:'tools'}},{id:'catalog',type:'resource',position:{x:1,y:1},data:{label:'Catalog',kind:'resource',provider:'tools'}}],edges:[],extensions:{engineeringModel:m}};
 const raw=JSON.stringify(toProjectFile(project));assert.deepEqual(parseProjectFile(raw).project.extensions.engineeringModel,m);assert.equal(m.elements.find(e=>e.id==='records').physicalMapping,undefined);
});
test('unknown types, duplicate member identity, ownership cycles and invalid view references reject',()=>{
 for(const mutate of [m=>m.elements.find(e=>e.id==='loan').attributes[0].typeRef='missing',m=>m.elements.find(e=>e.id==='loan').attributes[0].id='loan',m=>m.elements[0].ownerId='identity',m=>m.diagrams[0].placements[0].elementId='missing',m=>m.diagrams[0].relationships.push('missing'),m=>m.elements.find(e=>e.id==='loan').attributes[0].multiplicity={lower:2,upper:1}]){const m=libraryEngineeringModel();mutate(m);assert.throws(()=>validateEngineeringModel(m),/Engineering model:/);}
});
test('foreign keys preserve ordered column ownership, types, uniqueness and nullability',()=>{
 for(const mutate of [m=>m.relationships.find(r=>r.id==='loan-book').targetColumns=['books-title'],m=>m.relationships.find(r=>r.id==='loan-book').sourceColumns=['records-start'],m=>m.relationships.find(r=>r.id==='loan-book').onDelete='setNull',m=>m.elements.find(e=>e.id==='books').columns[0].nullable=true,m=>m.elements.find(e=>e.id==='records').indexes[0].columns=['books-id']]){const m=libraryEngineeringModel();mutate(m);assert.throws(()=>validateEngineeringModel(m),/Engineering model:/);}
});
test('diagram relationships require actual visible endpoints, not copied labels',()=>{const m=libraryEngineeringModel();m.diagrams[2].relationships=['service-loan'];assert.throws(()=>validateEngineeringModel(m),/visible endpoints/);});

test('module handoffs retain one complete typed model and explicit ownership without assigning adjacent entities',async()=>{
 const {createBlockHandoff}=await import('../src/block-handoff.mjs');
 const {blockSpecPath}=await import('../src/block-spec-kit.mjs');
 const model=libraryEngineeringModel();
 const project={version:1,revision:1,name:'Library',provider:'tools',nodes:['loans','catalog'].map((id,i)=>({id,type:'resource',position:{x:i*400,y:0},data:{label:id,kind:'resource',provider:'tools'}})),edges:[],extensions:{engineeringModel:model}};
 const handoff=createBlockHandoff(JSON.stringify(toProjectFile(project)),'loans');
 const exported=JSON.parse(handoff.files['spec-kit/system/engineering-model.json']);
 assert.deepEqual(exported,model);
 validateEngineeringModel(exported);
 const assignment=JSON.parse(handoff.files[blockSpecPath('loans')+'/engineering-model.json']);
 assert.ok(assignment.assignedElementIds.includes('loan'));
 assert.ok(!assignment.assignedElementIds.includes('books'));
 assert.ok(exported.elements.some(e=>e.id==='books'));
 assert.deepEqual(handoff.blockIds,['loans']);
 assert.match(handoff.files[blockSpecPath('loans')+'/spec.md'],/engineering-model.json/);
});

test('generalization cycles reject while recursive associations remain representable',()=>{
 const model=libraryEngineeringModel();
 model.relationships.push({id:'self-link',name:'Prior agreement',kind:'association',source:'loan',target:'loan'});
 validateEngineeringModel(model);
 model.relationships.push({id:'inherits-a',name:'Specializes',kind:'generalization',source:'loan',target:'service'},{id:'inherits-b',name:'Specializes',kind:'generalization',source:'service',target:'loan'});
 assert.throws(()=>validateEngineeringModel(model),/generalization contains a cycle/);
});

test('removing a linked block preserves the shared model through save, reopen and handoff',async()=>{
 const {architectureConsistency}=await import('../src/architecture-consistency.mjs');
 const {createBlockHandoff}=await import('../src/block-handoff.mjs');
 const model=libraryEngineeringModel();
 const project={version:1,revision:2,name:'Library',provider:'tools',nodes:[
  {id:'catalog',type:'resource',position:{x:0,y:0},data:{label:'Catalog',kind:'resource',provider:'tools'}},
 ],edges:[],extensions:{engineeringModel:model}};
 const saved=JSON.stringify(toProjectFile(project));
 const reopened=parseProjectFile(saved).project;
 assert.deepEqual(reopened.extensions.engineeringModel,model);
 assert.ok(architectureConsistency(reopened).issues.some(issue=>issue.code==='model_block_missing'&&issue.ref==='loans'));
 assert.throws(()=>validateEngineeringModel(model,{blockIds:['catalog']}),/unknown architecture block/);
 const handoff=createBlockHandoff(saved,'catalog');
 assert.deepEqual(JSON.parse(handoff.files['spec-kit/system/engineering-model.json']),model);
 assert.equal(JSON.parse(handoff.files['handoff-readiness.json']).status,'inconsistent_design');
});
