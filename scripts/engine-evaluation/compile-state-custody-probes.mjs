// Visible transfer diagnostics, never production dispatch or hidden acceptance.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
import {compositionFixture} from './composition-fixtures.mjs';import {terraformSketch} from '../../src/terraform.mjs';
const folder=process.argv[2];if(!folder||fs.existsSync(folder))throw Error('Choose a fresh output directory and preserve earlier evidence.');
const cases=[];
function write(name,project,backend){
 project={...project,decisions:[{id:'state-selection',title:'Preserve platform custody',subject:'state',status:'Proposed',decision:'Use the explicitly selected backend without migrating or replacing the platform store.'}],extensions:{...project.extensions,terraformState:{version:1,environments:{staging:{backend,owner:'Synthetic platform owner',residency:'Australia required; unverified fixture',decisionId:'state-selection'}}}}};
 const files=terraformSketch(project,'staging'),config=JSON.parse(files['main.tf.json']);
 if(Object.keys(config.terraform.backend).join(',')!==backend||config.variable.review_approved.default!==false||!config.locals.unfinished_work.includes('state-custody-and-operations-acceptance-required'))throw Error('State contract was not preserved.');
 for(const [file,body]of Object.entries(files)){const target=path.join(folder,name,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}
 fs.writeFileSync(path.join(folder,name+'-project.json'),JSON.stringify(project,null,2)+'\n');
 cases.push({name,backend,generatedDigests:Object.fromEntries(Object.entries(files).map(([file,body])=>[file,createHash('sha256').update(body).digest('hex')]))});
}
for(const provider of ['aws','azure','gcp','ibm'])for(const backend of ['s3','azurerm','gcs','http'])write(provider+'-'+backend,compositionFixture(provider),backend);
write('cross-provider-http',compositionFixture('cross-provider'),'http');
const solo=compositionFixture('gcp');write('standalone-gcp-s3',{...solo,nodes:[solo.nodes.at(-1)],edges:[]},'s3');
fs.writeFileSync(path.join(folder,'receipt.json'),JSON.stringify({cases,boundary:'Explicit root backend transfer configuration; remote access, locks, recovery, migration and runtime remain unverified.'},null,2)+'\n');console.log('Generated eighteen state custody transfer packages.');
