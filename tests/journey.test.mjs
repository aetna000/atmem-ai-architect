import test from 'node:test';
import assert from 'node:assert/strict';
import {pdmTemplate,validateImport} from '../src/core.mjs';
import {understand,opening,nextQuestion,progress,sketch,extractFacts,extractRequirements,TOPICS,WORKFLOWS} from '../src/discovery.mjs';
import {review,acceptRisk,blockers} from '../src/review.mjs';
import {estimate,setPrice,setUsage,DISCLAIMER} from '../src/estimate.mjs';
import {deploymentDocument} from '../src/document.mjs';
import {cleanEngagement} from '../src/engagement.mjs';
import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
const empty=()=>({version:1,revision:1,name:'New project',nodes:[],edges:[]});
const talk=(p,...ms)=>{let body;for(const m of ms){({project:p,body}=understand(m,p));}return {p,body};};

test('discovery starts open, then asks the skill\'s own questions before platform choices',()=>{
  assert.match(opening(empty()),/What should this system help someone do\?/);
  const {p,body}=talk(empty(),'A company-wide AI system over our shared files, plus a chatbot');
  assert.equal(p.workflow,'knowledge-assistant');assert.match(body,/Sounds like RAG/);assert.equal(p.name,'A company-wide AI system over our shared…');
  assert.match(body,/Where do the files live/);assert.equal((body.match(/\?/g)||[]).length,1);
  const q=talk(p,'SharePoint, about 20k files').p;assert.notEqual(q.lastAsked.id,p.lastAsked.id);assert.match(q.brief.data,/SharePoint/);
  let r=q;for(let i=0;i<8&&r.lastAsked;i++){if(['cloud','budget'].includes(r.lastAsked.topic))break;r=talk(r,'not sure').p;}
  assert.ok(['cloud','budget'].includes(r.lastAsked?.topic)||!r.lastAsked,'cloud and budget come last');
});
test('answers are filed under the topic just asked, even without keywords',()=>{
  let {p}=talk(empty(),'A tool that writes poems for our newsletter');
  assert.equal(p.lastAsked.topic,'data');
  p=talk(p,'mostly the old archive').p;
  assert.match(p.brief.data,/old archive/);
});
test('“not sure” becomes a stated assumption and an open question, never a blocker',()=>{
  let {p}=talk(empty(),'A tool that writes poems for our newsletter','the old archive','50 people','nothing yet','within 10 seconds');
  assert.equal(p.lastAsked.topic,'cloud');
  const r=understand('no idea',p);
  assert.match(r.body,/let's assume/);assert.match(r.project.brief.cloud,/^Not sure yet/);
  assert.ok(r.project.assumptions.some(a=>/No preference yet/.test(a.statement)));
  assert.ok(r.project.openQuestions.some(q=>/cloud provider/.test(q.question)));
  assert.equal(progress(r.project).find(t=>t.id==='cloud').state,'assumed');
  const later=understand('actually we are on AWS',r.project).project;
  assert.equal(later.brief.cloud,'AWS');assert.equal(later.openQuestions.find(q=>/cloud provider/.test(q.question)).status,'answered');
});
test('numbers with units become facts; quality statements become measurable requirements',()=>{
  const f=extractFacts('about 300 staff, 2,000 questions a month, 40 GB of PDFs, £2k per month, includes patient data, we use Azure');
  const get=(n)=>f.find(x=>x.name===n)?.value;
  assert.equal(get('users'),300);assert.equal(get('requests.per_month'),2000);assert.equal(get('data.gb'),40);assert.equal(get('budget.per_month'),2000);assert.equal(get('data.sensitive'),true);assert.equal(get('cloud.preference'),'azure');
  assert.equal(extractFacts('50 tickets a day')[0].value,1500);
  const r=extractRequirements('answers within 5 seconds, 99.9% uptime, data must stay in the EU, a manager approves refunds');
  assert.deepEqual(r.map(x=>x.category),['performance','availability','compliance','security']);
  assert.deepEqual(r[0].measure,{metric:'p95 response time',op:'<=',target:5,unit:'s'});
});
test('ambiguous dollar budgets keep currency unknown across unrelated client domains',()=>{
 assert.equal(extractFacts('We check fraud 500 requests per day').some(f=>f.name==='budget.per_month'),false);
 for(const brief of ['Library booking system in Australia, budget $500 per month','Warehouse intake in Canada, $500 per month','Member website in New Zealand, $500 per month']){
  const budget=extractFacts(brief).find(f=>f.name==='budget.per_month');
  assert.equal(budget.value,500);assert.equal(budget.currency,null);assert.equal(budget.unit,'currency unspecified/month');assert.equal(budget.text,brief);
 }
 for(const [symbol,currency]of [['A$','AUD'],['AU$','AUD'],['CAD','CAD'],['US$','USD'],['NZ$','NZD'],['£','GBP'],['€','EUR']]){
  const budget=extractFacts(`Budget ${symbol}600 per year`).find(f=>f.name==='budget.per_month');assert.equal(budget.currency,currency);assert.equal(budget.value,50);
 }
});
test('conflicting numbers keep both with dates and ask which is current',()=>{
  const {p,body}=talk(empty(),'chatbot for policies','100 staff','sorry, 250 staff');
  assert.equal(p.facts.filter(f=>f.name==='users').length,2);assert.match(body,/Which is current/);
});
test('every workflow skill detects, asks its own questions first and sketches on all four clouds',()=>{
  const said={'knowledge-assistant':'answer questions from our policy documents','document-processing':'extract fields from supplier invoices','predictive':'predict pump failure from sensor data','agentic-automation':'automate ticket triage and routing'};
  for(const w of WORKFLOWS.filter(w=>w.detect)){
    const {p}=talk(empty(),said[w.id]);assert.equal(p.workflow,w.id,w.id);
    assert.ok(p.lastAsked.id.startsWith(w.id),`${w.id} asks its own question first`);
    for(const cloud of ['AWS','Azure','Google Cloud','IBM']){
      const s=sketch({...p,facts:[...p.facts,...extractFacts(`we use ${cloud}`)]});
      assert.doesNotThrow(()=>validateImport(s.next),`${w.id} ${cloud}`);assert.ok(s.next.nodes.length>=2);
    }
  }
});
test('the RAG concept draws only what was said or agreed',()=>{
  const labels=(p)=>sketch(p).next.nodes.map(n=>n.data.label);
  let {p}=talk(empty(),'I want a chatbot for our company documents');
  assert.deepEqual(labels(p),['Your documents','AI that answers from them','Chatbot']);
  p=talk(p,'SharePoint, about 20k files').p;assert.deepEqual(labels(p),['SharePoint & OneDrive files','AI that answers from them','Chatbot']);
  p=talk(p,'yes').p;assert.ok(labels(p).includes('Permissions sync (who sees what)'),'yes to the permissions question adds it');
  p=talk(p,'in Teams').p;assert.ok(labels(p).includes('Microsoft Teams bot'));
  p=talk(p,'we use Entra ID').p;assert.ok(labels(p).includes('Company sign-in (SSO)'));
  p=talk(p,'we are on Azure').p;assert.ok(labels(p).includes('Microsoft Entra ID'));assert.ok(labels(p).includes('Microsoft Foundry models'));
  for(const extra of ['Vector index','Guardrails','Feedback & evaluation','Connectors & sync'])assert.ok(!labels(p).some(l=>l.includes(extra)),`${extra} was never mentioned`);
  const no=talk(talk(talk(empty(),'a chatbot for our documents').p,'a shared drive').p,'no').p;assert.ok(!labels(no).includes('Permissions sync (who sees what)'));
});
test('review: guardrail gap is a blocker; findings cite rules; accepted risk persists',()=>{
  let {p}=talk(empty(),'a chatbot over our documents, with guardrails');
  p={...p,...sketch(p).next};
  assert.equal(blockers(review(p)).length,0);
  p={...p,edges:[...p.edges.filter(e=>e.source!=='guard'&&e.target!=='guard'),{id:'skip',source:'llm',target:'chat',label:'answer'}]};
  const f=review(p);const b=blockers(f);assert.equal(b.length,1);assert.equal(b[0].rule,'SEC-001');assert.match(b[0].source,/rule SEC-001 v1/);
  assert.throws(()=>acceptRisk(p,b[0],'',''),/reason and an owner/);
  const q=acceptRisk(p,b[0],'Internal pilot only','Matt');
  assert.equal(blockers(review(q)).length,0);assert.equal(review(q).find(x=>x.rule==='SEC-001').status,'accepted');
  for(const rule of ['REL-001','AVL-001','PRF-001','SCL-001','CST-001','DSN-001'])assert.ok(f.some(x=>x.rule===rule),rule);
  const plain={...talk(empty(),'a chatbot over our documents').p};const drawn={...plain,...sketch(plain).next};
  assert.equal(blockers(review(drawn))[0]?.rule,'SEC-001','a chatbot with no guardrail is flagged, not silently fixed');
});
test('review: sensitive data needs residency; automated actions need approval',()=>{
  const p=pdmTemplate();
  assert.ok(review(p).some(f=>f.rule==='SEC-002'));
  const q={...p,needs:[{id:'r',kind:'nonfunctional',category:'compliance',statement:'Data stays in the EU',priority:'must',status:'open',source:'user',links:[]}]};
  assert.ok(!review(q).some(f=>f.rule==='SEC-002'));
});
test('estimate: quantity × sourced price; missing inputs and prices leave it incomplete',()=>{
  let {p}=talk(empty(),'answer questions from our documents','300 staff, 2000 questions a month','40 GB of PDFs','we use AWS');
  p={...p,...sketch(p).next};
  let e=estimate(p);
  const llm=e.lines.find(l=>l.driver==='Model tokens');
  assert.equal(llm.status,'input needed');assert.deepEqual(llm.missing,['tokens_per_request']);assert.equal(e.complete,false);
  p=setUsage(p,'tokens_per_request',3000);
  e=estimate(p);assert.equal(e.lines.find(l=>l.driver==='Model tokens').quantity,6000);assert.equal(e.lines.find(l=>l.driver==='Model tokens').status,'price needed');
  for(const l of e.lines)p=setPrice(p,l.id,{price:l.driver==='Model tokens'?0.01:0.5,currency:'USD'});
  e=estimate(p);assert.equal(e.complete,false);assert.ok(e.gaps.length>0); // Coarse lines still need service/region and full component coverage.
  const expected=e.lines.reduce((s,l)=>s+l.cost,0);assert.equal(e.expected,Math.round(expected*100)/100);
  assert.equal(e.low,Math.round(expected*0.7*100)/100);assert.equal(e.drivers[0].driver,'Model tokens');
  assert.ok(e.lines.every(l=>l.price.source==='entered by you'&&l.price.date));
  assert.equal(estimate(setPrice(p,e.lines[0].id,{currency:'EUR'})).mixedCurrencies,true);
});
test('estimate survives the project file round trip and is sanitised',()=>{
  let p=setPrice(setUsage(pdmTemplate(),'tokens_per_request',2500),'insights',{price:0.02,url:'https://example.com/pricing'});
  p=validateImport(p);
  const back=fromProjectFile(JSON.parse(JSON.stringify(toProjectFile(p)))).project;
  assert.deepEqual(back.estimate,p.estimate);
  assert.equal(cleanEngagement({estimate:{usage:{x:-1},prices:{a:{price:'free'}}}}).estimate.prices.a.price,undefined);
});
test('deployment document: every section, every assumption and open question, blockers flagged',()=>{
  let {p}=talk(empty(),'a chatbot over our documents, with guardrails','300 staff, 2000 questions a month','not sure','within 5 seconds');
  p={...p,...sketch(p).next};
  const md=deploymentDocument(p,null);
  for(const h of ['## 1. Summary','## 2. Scope and context','## 3. Architecture','## 4. Data flows','## 5. Security controls','## 6. Requirements','## 7. Review findings','## 8. Cost estimate','## 9. Deployment steps','## 10. Decisions','## 11. Assumptions','## 12. Open questions'])assert.ok(md.includes(h),h);
  for(const a of p.assumptions)assert.ok(md.includes(a.statement),a.statement);
  for(const q of p.openQuestions.filter(q=>q.status==='open'))assert.ok(md.includes(q.question),q.question);
  assert.ok(md.includes(DISCLAIMER));assert.match(md,/Responds within 5 s/);
  assert.match(md,/No blockers found/);
  const broken={...p,edges:[...p.edges.filter(e=>!e.target.startsWith('guard')),{id:'x',source:p.nodes.find(n=>n.data.role==='llm').id,target:p.nodes.find(n=>n.data.role==='app').id}]};
  assert.match(deploymentDocument(broken,null),/Not ready for deployment/);
});

test('the general AI architecture skill covers anything without a specialised fit, and draws only what was said',()=>{
  const {p}=talk(empty(),'Something that helps our sales team with our CRM data');
  assert.equal(p.workflow,'general');
  const s=sketch(p).next;assert.deepEqual(s.nodes.map(n=>n.data.label),['CRM','AI model']);
  const q=talk(p,'they would use it in Teams').p;assert.deepEqual(sketch(q).next.nodes.map(n=>n.data.label),['CRM','AI model','Microsoft Teams']);
});
test('the skill switches when the user\'s words clearly fit another one',()=>{
  let r=understand('A chatbot that answers questions from our policy documents',empty());
  assert.equal(r.project.workflow,'knowledge-assistant');
  r=understand('actually it should automate ticket triage and route tickets to the right team',r.project);
  assert.equal(r.project.workflow,'agentic-automation');assert.match(r.body,/switching skills/);
  const stay=understand('about 300 staff',r.project);assert.equal(stay.project.workflow,'agentic-automation');
});
