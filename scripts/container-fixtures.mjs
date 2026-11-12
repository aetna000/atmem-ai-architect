import {terraformSketch} from '../src/terraform.mjs';
import {CONTAINER_SERVICES} from '../src/container-contracts.mjs';
import fs from 'node:fs';import path from 'node:path';
const root=process.argv[2];if(!root)throw Error('Supply an output directory for generated fixtures.');
for(const [provider,c] of Object.entries(CONTAINER_SERVICES)){
 const p={version:1,revision:1,name:'Container qualification',provider,nodes:[{id:'app',type:'resource',position:{x:0,y:0},data:{label:'Application',kind:'resource',provider,origin:'proposed',service:c.service,implementation:'container-service'}}],edges:[]};
 for(const [name,body] of Object.entries(terraformSketch(p))){const file=path.join(root,provider,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,body);}
}
