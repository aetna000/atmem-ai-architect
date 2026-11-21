import test from 'node:test';import assert from 'node:assert/strict';
import {componentReviews,markComponentReviewed,applyComponentReview,reviewIssueLabel} from '../src/component-review.mjs';
import {validateImport} from '../src/core.mjs';import {toProjectFile,parseProjectFile} from '../src/project-file.mjs';
const emptyProject=()=>({id:'review-project',version:1,revision:1,name:'Review project',provider:'tools',requirements:'',nodes:[],edges:[]});
const node=(id)=>({id,type:'resource',position:{x:0,y:0},data:{label:id,description:'Existing external browser owned by the visitor.',kind:'resource',provider:'tools',origin:'existing',config:{region:'External client',classification:'Public'}}});
const project=()=>({...emptyProject(),nodes:[node('browser'),node('site')],edges:[{id:'load',source:'browser',target:'site',label:'HTTPS load'}]});
test('each block starts unreviewed; explicit confirmation persists without claiming runtime validation',()=>{
 const p=project();assert.equal(componentReviews(p)[0].status,'ready');
 const next=markComponentReviewed(p,'browser');assert.equal(componentReviews(next)[0].status,'reviewed');assert.equal(componentReviews(next)[1].status,'ready');
 assert.equal(next.extensions.componentReviews.browser.scope,'user_design_review_not_runtime_validation');
 const reopened=parseProjectFile(JSON.stringify(toProjectFile(validateImport(next))));assert.equal(componentReviews(reopened.project)[0].status,'reviewed');
});
test('questions and missing detail block confirmation; answers are retained per block',()=>{
 const p=project();p.openQuestions=[{id:'q',question:'Which account owns this?',status:'open',answer:'',links:['browser']}];assert.equal(componentReviews(p)[0].status,'questions');assert.equal(componentReviews(p)[1].status,'ready');assert.throws(()=>markComponentReviewed(p,'browser'));
 p.openQuestions[0]={...p.openQuestions[0],status:'answered',answer:'The visitor owns the browser.'};assert.equal(componentReviews(p)[0].status,'ready');assert.equal(componentReviews(markComponentReviewed(p,'browser'))[0].status,'reviewed');
 p.nodes[1].data.description='';assert.equal(componentReviews(p)[1].status,'questions');
});
test('semantic changes invalidate review while moving nodes does not',()=>{
 const p=markComponentReviewed(project(),'browser');const moved=structuredClone(p);moved.nodes[0].position.x=500;assert.equal(componentReviews(moved)[0].status,'reviewed');
 for(const change of [p=>p.nodes[0].data.description+=' Changed.',p=>p.nodes[1].data.description+=' Changed neighbor.',p=>p.edges[0].label='Different contract',p=>p.needs=[{id:'req',statement:'New behavior',kind:'functional',links:['browser']}],p=>p.decisions=[{id:'decision',decision:'New ownership'}]]){const next=structuredClone(p);change(next);assert.equal(componentReviews(next)[0].status,'changed');}
});
test('notes are excluded; a cloud deployment needs a region; architecture findings remain design issues',()=>{
 const p=project();p.nodes.push({...node('note'),data:{kind:'note',label:''}});assert.equal(componentReviews(p).length,2);
 p.nodes[0].data={...p.nodes[0].data,provider:'aws',origin:'proposed',config:{region:'To be selected'}};assert.ok(componentReviews(p)[0].issues.some(i=>i.text.includes('region')));
 p.nodes[0].data={...p.nodes[0].data,provider:'tools',kind:'agent',origin:'existing'};p.nodes[1].data.kind='output';assert.ok(componentReviews(p)[0].issues.some(i=>i.kind==='finding'));
});

test('architect notes create scoped questions without approving, erasing answers or changing the diagram',()=>{
 const p=project(),target=componentReviews(p)[0],result={componentId:'browser',summary:'Browser ownership is clear; identity recovery needs a decision.',questions:['How is anonymous identity recovered?']};
 const next=applyComponentReview(p,target,result);assert.equal(next.openQuestions.length,1);assert.deepEqual(next.openQuestions[0].links,['browser']);assert.equal(componentReviews(next)[0].status,'questions');assert.equal(componentReviews(next)[0].architectNote,result.summary);assert.deepEqual(next.nodes,p.nodes);
 const repeated=applyComponentReview(next,componentReviews(next)[0],result);assert.equal(repeated.openQuestions.length,1);
 repeated.openQuestions[0]={...repeated.openQuestions[0],status:'answered',answer:'User signs in to recover the account.'};const answered=applyComponentReview(repeated,componentReviews(repeated)[0],{...result,questions:[]});assert.equal(answered.openQuestions[0].answer,'User signs in to recover the account.');assert.equal(componentReviews(answered)[0].status,'ready');assert.equal(componentReviews(answered)[0].architectNote,result.summary);
 const reopened=parseProjectFile(JSON.stringify(toProjectFile(validateImport(answered)))).project;assert.equal(reopened.openQuestions[0].answer,answered.openQuestions[0].answer);
});
test('stale or wrong-block model reviews cannot attach questions or notes',()=>{
 const p=project(),target=componentReviews(p)[0];p.nodes[0].data.description+=' Changed.';
 assert.throws(()=>applyComponentReview(p,target,{componentId:'browser',summary:'Stale',questions:[]}));
 assert.throws(()=>applyComponentReview(p,componentReviews(p)[0],{componentId:'site',summary:'Wrong',questions:[]}));
});
test('topology responsibility survives project and agent serialization without silent clipping',async()=>{
 const {toAgentProject}=await import('../src/local-agent.mjs');const p=project();p.nodes[0].data.topologyGroup='User experience';const checked=validateImport(p);assert.equal(toAgentProject(checked).nodes[0].data.topologyGroup,'User experience');assert.equal(parseProjectFile(JSON.stringify(toProjectFile(checked))).project.nodes[0].data.topologyGroup,'User experience');p.nodes[0].data.topologyGroup='x'.repeat(101);assert.throws(()=>validateImport(p),/no content was truncated/);
});

test('recorded block answers remain in model context instead of disappearing as closed questions',async()=>{
 const {agentContext}=await import('../src/local-agent.mjs');const p=validateImport(project());p.openQuestions=[{id:'answer',question:'Who owns it?',answer:'The client.',status:'answered',links:['browser']}];assert.ok(agentContext(p).some(c=>c.id==='answer'&&c.text.includes('The client.')));
});
test('editing a linked requirement records user wording and invalidates all affected block reviews',async()=>{
 const {editBlockRequirement}=await import('../src/component-review.mjs');let p=project();p.needs=[{id:'req-shared',statement:'Original behavior',kind:'functional',category:'other',priority:'must',status:'open',source:'agent',links:['browser','site']}];p=markComponentReviewed(markComponentReviewed(p,'browser'),'site');
 const next=editBlockRequirement(p,'browser','req-shared','New behavior agreed by the user');assert.equal(next.needs[0].statement,'New behavior agreed by the user');assert.equal(next.needs[0].source,'user');assert.equal(next.extensions.requirementEditHistory[0].previousStatement,'Original behavior');assert.deepEqual(componentReviews(next).map(r=>r.status),['changed','changed']);assert.deepEqual(next.nodes,p.nodes);
 assert.throws(()=>editBlockRequirement(p,'browser','missing','Edit'));assert.throws(()=>editBlockRequirement(p,'browser','req-shared',' '));
});

test('monitoring findings are design issues, not questions or completed work',()=>{
 const p=project();p.nodes[0].data.role='llm';const item=componentReviews(p)[0];
 assert.ok(item.issues.some(i=>i.kind==='finding'&&i.text==='No monitoring for model quality or drift.'));
 assert.equal(item.status,'issues');assert.equal(item.statusLabel,'Needs attention');assert.match(reviewIssueLabel(item.issues),/design issue/);assert.doesNotMatch(reviewIssueLabel(item.issues),/question/);assert.throws(()=>markComponentReviewed(p,item.id));
 p.openQuestions=[{id:'owner',question:'Who receives alerts?',status:'open',links:[item.id]}];
 const mixed=componentReviews(p)[0];assert.match(reviewIssueLabel(mixed.issues),/^1 question · \d+ design issues?$/);
 assert.equal(reviewIssueLabel([{kind:'question'}]),'1 question');assert.equal(reviewIssueLabel([{kind:'finding'}]),'1 design issue');
});
