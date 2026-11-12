// Visible compiler diagnostics, not a held-out benchmark or production dispatch.
import fs from 'node:fs';import path from 'node:path';
import {terraformSketch} from '../../src/terraform.mjs';import {invoiceProject} from '../../tests/fixtures/invoice-project.mjs';import {CONTAINER_SERVICES} from '../../src/container-contracts.mjs';
const folder=process.argv[2];if(!folder||fs.existsSync(folder))throw Error('Choose a new output directory; previous evidence is preserved.');
const container=(provider,id)=>({id:'composition-qualification',version:1,revision:1,name:'Independent scientific service',provider,requirements:'Preserve and run the supplied scientific image; no application implementation is inferred.',nodes:[{id,position:{x:0,y:0},data:{label:'Instrument application',kind:'resource',provider,origin:'proposed',implementation:'container-service',service:CONTAINER_SERVICES[provider].service}}],edges:[]});
const compile=project=>terraformSketch(project);
function write(name,files){for(const [file,body]of Object.entries(files)){const target=path.join(folder,name,file);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,body);}}
const providers=Object.keys(CONTAINER_SERVICES);
for(const provider of providers){const p=invoiceProject(provider);p.nodes.push(...container(provider,'instrument-µ').nodes);write(provider,compile(p));write(provider+'-container',terraformSketch(container(provider,'instrument-µ')));}
const project={...container('aws','independent-inventory'),nodes:[...providers.flatMap(provider=>container(provider,provider+'-instrument').nodes),...container('aws','independent-inventory').nodes]};
for(const [name,gaps]of [['cross-provider',[]],['unimplemented-interface',['retained-required-business-interface']]]){
 const scoped={...project,edges:gaps.length?[{id:gaps[0],source:project.nodes[0].id,target:project.nodes[1].id,label:'Required business integration'}]:[]},files=compile(scoped),tf=JSON.parse(files['main.tf.json']),values={...JSON.parse(files['deployment.tfvars.json.example']),review_approved:true};
 files['tests/composition.tftest.hcl']=Object.entries(tf.provider).flatMap(([provider,configs])=>configs.map(config=>`mock_provider "${provider}" { alias = "${config.alias}" }`)).join('\n')+'\nvariables {\n'+Object.entries(values).map(([key,value])=>key+' = '+JSON.stringify(value)).join('\n')+'\n}\n'+(gaps.length?'run "preserved_interface_blocks_composition" {\n command = plan\n expect_failures = [terraform_data.review_gate]\n}\n':'run "independent_units_plan_together" { command = plan }\nrun "whole_composition_review_stays_required" {\n command = plan\n variables { review_approved = false }\n expect_failures = [terraform_data.review_gate]\n}\n');write(name,files);
}
console.log('Generated four mixed workflow/image packages, four standalone footprints and positive/negative five-unit cross-provider diagnostics at '+folder);
