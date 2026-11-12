import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync}from 'node:fs';import {createHash}from 'node:crypto';
import {approvalApplicationFiles}from '../src/approval-application-files.mjs';import {approvalProject}from './fixtures/approval-project.mjs';import {resourceAddress}from '../src/identifiers.mjs';
test('native-worker catalog and browser application exports preserve identical production modules and exact provider locks',()=>{
 const catalog=JSON.parse(readFileSync(new URL('../server/engineering_assets/application-runtime.json',import.meta.url),'utf8'));
 assert.equal(catalog.format,'atmem.shared-application-runtime');assert.equal(catalog.version,1);
 for(const provider of ['aws','azure','gcp','ibm']){
  const project=approvalProject(provider),files=approvalApplicationFiles(project,'staging'),root='applications/'+resourceAddress(project.nodes[0].id)+'/';
  assert.equal(files[root+'requirements.lock'],catalog.providers[provider].requirements);assert.equal(files[root+'test-requirements.lock'],catalog.providers[provider].testRequirements);
  for(const[name,content]of Object.entries(files).filter(([name])=>name.startsWith(root)&&name.endsWith('.py')&&!name.endsWith('/api.py'))){const relative=name.slice(root.length);assert.equal(content,catalog.files[relative].content);assert.equal(createHash('sha256').update(content).digest('hex'),catalog.files[relative].sha256);}
 }
 assert(Object.hasOwn(catalog.files,'workflow_process_stage.py'));assert(Object.hasOwn(catalog.files,'aws_json_model.py'));assert(Object.keys(catalog.files).every(name=>!name.startsWith('invoice')&&!name.includes('acceptance')));
});
