// Execution admission only. Native Terraform remains the independent validator.
// Original handoffs are read-only; never repair an artifact to make it pass.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {terraformSketch} from '../src/terraform.mjs';

export function invoiceCaseArtifact(directory, provider) {
 const caseRoot=fs.realpathSync(directory),handoff=path.join(caseRoot,'handoff');
 const read=name=>{
  const target=path.join(caseRoot,name);
  if(fs.realpathSync(target)!==target)throw Error('Artifact symlink is not admitted: '+name);
  return fs.readFileSync(target,'utf8');
 };
 const project=JSON.parse(read('project.json')),manifest=JSON.parse(read('handoff/manifest.json'));
 if(project.provider!==provider)throw Error('Artifact provider differs from requested provider');
 if(!['staging','production'].includes(manifest.environment)||manifest.deploymentExecuted!==false)throw Error('Invalid artifact environment or deployment boundary');
 const receipt=JSON.parse(read('export-assessment.json')),digests=receipt.digests;
 const current=terraformSketch(project,manifest.environment),files={};
 const inventory=manifest.files.filter(name=>name.startsWith('terraform/'));
 if(new Set(inventory).size!==inventory.length)throw Error('Duplicate Terraform inventory');
 for(const name of inventory){
  if(name.includes('\\')||name.split('/').some(part=>['','..','.'].includes(part)))throw Error('Unsafe artifact path');
  const relative=name.slice('terraform/'.length),body=read('handoff/'+name);
  if(createHash('sha256').update(body).digest('hex')!==digests?.[name])throw Error('Original export digest mismatch: '+name);
  // Exact reviewed compiler reproduction admits executable provider/test inputs.
  // This is not a quality score: schemas and mock plans still inspect these bytes.
  if(body!==current[relative])throw Error('Artifact no longer reproduces current compiler: '+name);
  files[relative]=body;
 }
 if(Object.keys(current).some(name=>!Object.hasOwn(files,name)))throw Error('Incomplete original Terraform inventory');
 if(!files['main.tf.json']||!files['tests/invoice.tftest.hcl'])throw Error('Not a complete invoice Terraform artifact');
 return {files,environment:manifest.environment,project,caseRoot,exportReceiptSha256:createHash('sha256').update(read('export-assessment.json')).digest('hex')};
}
