import test from 'node:test';
import assert from 'node:assert/strict';
import {findCredentials} from '../src/project-file.mjs';
import {architectureGraph} from '../src/architecture-diagram-geometry.mjs';
import {diagramProjection} from '../src/architecture-diagrams.mjs';
import {graphMermaid} from '../src/drawio-model.mjs';
test('ordinary supervisor and helpdesk identifiers survive credential inspection while actual key tokens remain blocked',()=>{
 for(const id of ['op-desk-confirm-workstation-status','helpdesk-service-create-session','task-handoff-attempt-number'])assert.deepEqual(findCredentials({id}),[]);
 assert.deepEqual(findCredentials({authorization:'Bearer sk-'+ 'a'.repeat(30)}),['authorization']);
 assert.deepEqual(findCredentials({token:'configured-value'}),['token']);
});
test('nullable foreign keys change their Mermaid cardinality and native connector notation',()=>{
 const table=(id)=>({id,name:id,kind:'table',basis:'proposed',source:'',details:[{name:'Columns',value:'id uuid NOT NULL PK'},{name:'Primary key',value:'id'}]});
 const model={version:1,elements:[table('child'),table('parent')],relations:[{id:'fk',name:'parent',kind:'foreign-key',basis:'proposed',source:'',from:'child',to:'parent',details:[{name:'Nullable',value:'false'},{name:'Unique',value:'false'},{name:'From columns',value:'id'},{name:'To columns',value:'id'}]}],views:[{id:'schema',name:'Schema',kind:'erd',elementIds:['child','parent'],relationIds:['fk'],gaps:[]}]};
 const before=architectureGraph(diagramProjection(model,model.views[0]),model.views[0]);
 model.relations[0].details[0].value='true';
 const after=architectureGraph(diagramProjection(model,model.views[0]),model.views[0]);
 assert.notEqual(graphMermaid(before),graphMermaid(after));assert.notEqual(before.wires[0].style,after.wires[0].style);
 assert.match(graphMermaid(after),/0\.\.1 parent/);
});

import {buildReview,designReadiness,reviewDecisions} from '../src/build-review.mjs';
const emptyProject=()=>({id:'fixture',revision:1,name:'Fixture',nodes:[],edges:[],needs:[],decisions:[],openQuestions:[],extensions:{}});
test('traceability uses explicit scenario requirement links, never unrelated adjacent interfaces',()=>{
 const project=emptyProject();project.needs=[{id:'need-a',statement:'Process a payment',links:['service']}];
 project.nodes=[{id:'service',data:{label:'Payment service',buildSpec:{scenarios:[{steps:[{requirementIds:['need-a'],interfaceId:'charge'},{requirementIds:['other-need'],interfaceId:'refund'}]}]}}}];
 project.edges=[{id:'charge',source:'service',target:'bank'},{id:'refund',source:'service',target:'bank'}];
 const review=buildReview(project);
 assert.deepEqual(review.requirements[0].interfaceIds,['charge']);
 assert.match(designReadiness(review).gaps.join(';'),/case definitions/);
 project.nodes[0].data.buildSpec.scenarios=[];
 assert.deepEqual(buildReview(project).requirements[0].interfaceIds,[]);
});
test('review keeps missing acceptance visible and deduplicates decision identities',()=>{
 const project=emptyProject();project.openQuestions=[{id:'region',question:'Which region?',status:'answered',answer:'Sydney'}];project.decisions=[{id:'region',subject:'cloud.region',status:'Accepted',decision:'Sydney'}];
 const review=buildReview(project);assert.equal(reviewDecisions(project,review).length,1);
 assert.equal(designReadiness(review,true).title,'Design gaps remain');
 assert.ok(designReadiness(review,true).gaps.includes('28 diagram types need content'));
});
test('a diagram application receipt is preserved as history and never counted as an architectural choice',()=>{
 const project=emptyProject();project.decisions=[{id:'revision',subject:'design.laboratory',status:'Accepted',decision:'Applied as design revision 2.'},{id:'choice',subject:'data.country',status:'Accepted',decision:'Australia'}];
 project.openQuestions=[{id:'transport',question:'Approve the laboratory contract',status:'open'}];
 assert.deepEqual(reviewDecisions(project).map(d=>d.id),['transport','choice']);
 project.decisions.push({id:'design-choice',subject:'design.site-placement',status:'Accepted',decision:'Keep operational control on site.'});
 assert.ok(reviewDecisions(project).some(d=>d.id==='design-choice'));
 assert.equal(project.decisions.length,3);
});
test('a fully populated provisional contract cannot be presented as qualified',()=>{
 const p=emptyProject();p.edges=[{id:'lab-peer',source:'lab',target:'peer',interfaceSpec:{transport:'Transport pending. Provisional',input:'SampleId',output:'Receipt',authorization:'Workload identity',failure:'Hold pending receipts for reconciliation',verification:'Replay the same sample'}}];
 const report=buildReview(p);assert.deepEqual(report.interfaces[0].missing,[]);assert.equal(report.interfaces[0].pending.length,1);assert.match(report.interfaces[0].pending[0],/Transport/);
 assert.equal(report.counts.contractReviews,1);
});

import {validateDiagramModel} from '../src/architecture-diagrams.mjs';
test('diagram repair diagnostics identify the exact conflicting record without echoing untrusted values',()=>{
 const model={version:1,elements:[{id:'shared',name:'Service',kind:'system',basis:'proposed',source:'',details:[]}],relations:[],views:[{id:'shared',name:'Context',kind:'context',elementIds:['shared'],relationIds:[],gaps:[]}]};
 assert.throws(()=>validateDiagramModel(model),/views\[0\]\.id duplicates elements\[0\]\.id/);
 model.views[0].id='page';model.elements[0].name='x'.repeat(181);
 assert.throws(()=>validateDiagramModel(model),/elements\[0\]\.name/);
});

test('one broadly tagged case cannot stand in for dedicated requirement evidence',()=>{
 const project=emptyProject();project.needs=[{id:'a',links:['module']},{id:'b',links:['module']}];project.nodes=[{id:'module',data:{label:'Module',buildSpec:{verificationCases:[{id:'shared',requirementIds:['a','b']}]}}}];
 let report=buildReview(project);assert.equal(report.counts.covered,2);assert.equal(report.counts.dedicatedCovered,0);assert.match(designReadiness(report,true).gaps.join(';'),/2 requirements need dedicated/);
 project.nodes[0].data.buildSpec.verificationCases.push({id:'a-only',requirementIds:['a']},{id:'b-only',requirementIds:['b']});report=buildReview(project);assert.equal(report.counts.dedicatedCovered,2);
});

import {caseSpecificityIssues}from'../src/verification-cases.mjs';
test('different labels and evidence filenames cannot disguise copied dedicated fixture bodies',()=>{
 const fixture={blockId:'checkout',setup:'Seat A is held by request H1.',input:'Request H1',action:'Replay H1',expected:'Return the saved receipt.'};
 const rows=[{...fixture,id:'a',requirementIds:['one'],evidence:'one.log'},{...fixture,id:'b',requirementIds:['two'],evidence:'two.log'}];
 assert.equal(caseSpecificityIssues(rows).length,1);
 rows[1].input='Request H2 for seat B';assert.equal(caseSpecificityIssues(rows).length,0);
});
