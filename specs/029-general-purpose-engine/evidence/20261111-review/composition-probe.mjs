// Run from repository root. Visible diagnostic, not a held-out quality benchmark.
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const load=p=>import(pathToFileURL(path.resolve(p)));
const {invoiceProject}=await load('tests/fixtures/invoice-project.mjs');
const {CONTAINER_SERVICES}=await load('src/container-contracts.mjs');
const {resourcePlan}=await load('src/resources.mjs');
const {terraformSketch}=await load('src/terraform.mjs');
const results=[];
for(const provider of ['aws','azure','gcp','ibm']){
 const base=invoiceProject(provider);
 const app={id:'independent-app',type:'resource',position:{x:900,y:0},data:{label:'Independent scheduling application',kind:'resource',provider,origin:'proposed',service:CONTAINER_SERVICES[provider].service,implementation:'container-service'}};
 const own=resourcePlan({...base,nodes:[app],edges:[]}).rows[0];
 const mixed=structuredClone(base);mixed.nodes.push(app);mixed.requirements+=' Also host an independent existing scheduling container, without changing the invoice workflow.';
 const plan=resourcePlan(mixed),tf=JSON.parse(terraformSketch(mixed)['main.tf.json']);
 const together=plan.rows.find(r=>r.id===app.id);
 const renamed=structuredClone(mixed);renamed.name='Unrelated client name';renamed.nodes.forEach((n,i)=>n.data.label='Responsibility '+i);renamed.nodes.reverse();
 results.push({provider,standaloneSupported:own.implemented,mixedImplemented:together.implemented,mixedGap:plan.gapDetails.filter(g=>g.componentIds?.includes(app.id)),preservedRequiredNode:!!together,requirementsPreserved:mixed.requirements.includes('independent existing scheduling container'),renamingAndReorderingPreserveSupport:resourcePlan(renamed).rows.find(r=>r.id===app.id).implemented===together.implemented,emittedStandaloneAddress:!!tf.resource?.[CONTAINER_SERVICES[provider].type]?.[own.address],boundary:'Local compiler composition diagnostic only; no model conversation, provider validation, runtime or cloud execution.'});
}
fs.writeFileSync('specs/029-general-purpose-engine/evidence/20261111-review/composition-probes.json',JSON.stringify({results},null,2)+'\n');
console.log(JSON.stringify(results.map(({provider,standaloneSupported,mixedImplemented})=>({provider,standaloneSupported,mixedImplemented})),null,2));
