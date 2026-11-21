// Visible lifecycle transfer probes; no deployment or cloud access.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
import {compositionFixture} from './composition-fixtures.mjs';import {CONTAINER_SERVICES} from '../../src/container-contracts.mjs';
import {importPulumiSnapshot,snapshotToProject} from '../../src/pulumi.mjs';import {terraformSketch} from '../../src/terraform.mjs';
const folder=process.argv[2];if(!folder||fs.existsSync(folder))throw Error('Choose fresh output and preserve prior artifacts.');
const types={aws:'aws:ecs/service:Service',azure:'azure-native:app:ContainerApp',gcp:'gcp:cloudrunv2/service:Service',ibm:'ibm:codeengine:App'},cases=[];
for(const provider of Object.keys(types)){
 const project=compositionFixture(provider),urn='urn:pulumi:observed::external-platform::'+types[provider]+'::preserved-runtime';
 const imported=snapshotToProject(importPulumiSnapshot({resources:[{urn,type:types[provider],inputs:{password:'discarded-synthetic-input'},outputs:{token:'discarded-synthetic-output'}}]}));
 imported.nodes[0].data.origin='imported Pulumi state';imported.nodes[0].data.implementation='container-service';imported.nodes[0].data.deploymentMode='reference';
 project.nodes.push(imported.nodes[0],{id:'preserved-µ',position:{x:0,y:900},data:{label:'Already running service',kind:'resource',provider,origin:'existing',binding:'existing-service',deploymentMode:'reference',service:CONTAINER_SERVICES[provider].service,implementation:'container-service'}});
 project.extensions=imported.extensions;project.nodes.find(n=>n.id==='instrument-µ').data.config={region:{aws:'eu-west-1',azure:'westeurope',gcp:'europe-west1',ibm:'eu-de'}[provider]};project.requirements+=' Preserve both the observed externally owned cloud deployment and the already running service; deploy the separately supplied instrument image as a new footprint. No state adoption is authorized.';
 const files=terraformSketch(project),quality=JSON.parse(files['generation-quality.json']),ownership=JSON.parse(files['deployment-ownership.json']);
 if(quality.fatalFindings.length||!quality.infrastructureComplete)throw Error('Lifecycle fixture lost implementation/reference scope.');
 for(const id of ['observed-0','preserved-µ']){const entry=ownership.components.find(c=>c.id===id);if(entry.disposition!=='reference_only'||entry.managedAddresses.length)throw Error('Reference gained managed ownership.');}
 if(JSON.stringify(project).includes('discarded-synthetic-'))throw Error('Secret-bearing input/output fields survived metadata import.');
 for(const [file,body]of Object.entries(files)){const target=path.join(folder,provider,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
 fs.writeFileSync(path.join(folder,provider+'-project.json'),JSON.stringify(project,null,2)+'\n');
 cases.push({provider,urn,generatedDigests:Object.fromEntries(Object.entries(files).map(([file,body])=>[file,createHash('sha256').update(body).digest('hex')])),preserved:['observed-0','preserved-µ']});
}
fs.writeFileSync(path.join(folder,'receipt.json'),JSON.stringify({cases,boundary:'Observed state/reference/existing-source-create transfer diagnostics only. No cloud refresh, state import or runtime behavior established.'},null,2)+'\n');console.log('Generated four provider lifecycle packages.');
