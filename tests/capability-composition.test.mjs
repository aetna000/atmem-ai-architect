import test from 'node:test';import assert from 'node:assert/strict';
import {planCapabilityComposition,deliveryUnitProject} from '../src/capability-composition.mjs';import {resourcePlan} from '../src/resources.mjs';import {invoiceProject} from './fixtures/invoice-project.mjs';import {INVOICE_SERVICES} from '../src/invoice-plan.mjs';import {containerContract,CONTAINER_SERVICES} from '../src/container-contracts.mjs';
const contracts=[{id:'invoice-workflow',matches:n=>n.data.implementation==='invoice-workflow'&&n.data.origin==='proposed'&&n.data.service===INVOICE_SERVICES[n.data.provider]},{id:'container-service',matches:containerContract}];
const addService=(p,id,provider=p.provider)=>p.nodes.push({id,position:{x:1000,y:0},data:{label:'Unfamiliar laboratory scheduler',provider,kind:'resource',origin:'proposed',implementation:'container-service',service:CONTAINER_SERVICES[provider].service}});
for(const provider of Object.keys(CONTAINER_SERVICES))test(provider+': explicit capabilities retain complete graph scope and external ownership across rename/reorder',()=>{
 const p=invoiceProject(provider);addService(p,'laboratory-µ');const before=structuredClone(p),plan=planCapabilityComposition(p,contracts,resourcePlan);
 assert.equal(plan.composition.units.length,2);assert(plan.rows.every(r=>r.implemented));assert.deepEqual(plan.gapDetails,[]);assert(plan.connections.every(e=>e.generated));assert.equal(plan.invoicePlan.entries.length,1);assert.equal(plan.rows.find(r=>r.id==='accounting').existing,true);assert.equal(plan.rows.find(r=>r.id==='invoice').modulePath,'units/unit_696e766f696365');assert.deepEqual(p,before);
 const other=structuredClone(p);other.nodes.reverse();other.nodes.forEach((n,i)=>n.data.label='Different business '+i);other.name='Climate operations';assert.deepEqual(planCapabilityComposition(other,contracts,resourcePlan).composition,plan.composition);
 const child=deliveryUnitProject(p,'laboratory-µ');assert.deepEqual(child.nodes.map(n=>n.id),['laboratory-µ']);assert.equal(child.requirements,p.requirements);assert.deepEqual(child.needs,p.needs);
});
test('multiple invoice units preserve separate boundaries; an unconnected second unit stays blocked',()=>{
 const p=invoiceProject('aws');p.nodes.push({...structuredClone(p.nodes[1]),id:'second'});let plan=planCapabilityComposition(p,contracts,resourcePlan);assert.equal(plan.invoicePlan.entries.length,2);assert(plan.gapDetails.some(g=>g.id.includes('invoice-browser-contract')&&g.componentIds.includes('second')));assert(plan.gapDetails.some(g=>g.id.includes('invoice-accounting-contract')&&g.componentIds.includes('second')));
 p.edges.push({...structuredClone(p.edges[0]),id:'second-browser',target:'second'},{...structuredClone(p.edges[1]),id:'second-accounting',source:'second'});plan=planCapabilityComposition(p,contracts,resourcePlan);assert.deepEqual(plan.gapDetails,[]);assert.equal(plan.invoicePlan.entries.length,2);assert(plan.connections.every(e=>e.generated));
});
test('unknown units and inter-unit connections are retained rather than absorbed into a familiar contract',()=>{
 const p=invoiceProject('gcp');addService(p,'lab','aws');p.nodes.push({id:'required-store',data:{label:'Required owned data service',kind:'resource',provider:'gcp',origin:'proposed'}});p.edges.push({id:'lab-invoices',source:'lab',target:'invoice',integration:'unknown-api',label:'Retain this business interface'});const plan=planCapabilityComposition(p,contracts,resourcePlan);
 assert.equal(plan.rows.length,p.nodes.length);assert.equal(plan.connections.length,p.edges.length);assert.equal(plan.rows.find(r=>r.id==='required-store').implemented,false);assert(plan.gapDetails.some(g=>g.componentIds?.includes('required-store')));assert(plan.gapDetails.some(g=>g.edgeIds?.includes('lab-invoices')));assert.equal(plan.rows.find(r=>r.id==='lab').provider,'aws');
});
test('ambiguous registration and duplicate ownership cannot silently overwrite a unit',()=>{
 const p=invoiceProject('aws');addService(p,'lab');assert.throws(()=>planCapabilityComposition(p,[contracts[0],contracts[0]],resourcePlan),/uniquely registered/);p.nodes.push(structuredClone(p.nodes[1]));assert.throws(()=>planCapabilityComposition(p,contracts,resourcePlan),/unique component/);
});
test('overlapping capability matches stay ambiguous while independent units remain available',()=>{
 const p=invoiceProject('aws');addService(p,'lab-one');addService(p,'lab-two');const overlap={id:'different-policy',matches:contracts[0].matches},plan=planCapabilityComposition(p,[...contracts,overlap],resourcePlan);
 assert.equal(plan.composition.units.length,2);assert.equal(plan.rows.find(r=>r.id==='invoice').implemented,false);assert(plan.gapDetails.some(g=>g.id.startsWith('ambiguous-capability-')&&g.componentIds.includes('invoice')));assert.equal(plan.connections.length,p.edges.length);assert.equal(plan.invoicePlan.entries.length,0);
});
test('an adapter cannot claim an interface outside its declared unit boundary',()=>{
 const p=invoiceProject('aws');addService(p,'lab');const planner=scoped=>{const result=resourcePlan(scoped);if(scoped.nodes.length===1&&scoped.nodes[0].id==='lab')result.connections.push({id:'approved-action',source:'invoice',target:'accounting',generated:true});return result;};
 assert.throws(()=>planCapabilityComposition(p,contracts,planner),/outside its declared unit boundary/);
});
