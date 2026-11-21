import test from 'node:test';import assert from 'node:assert/strict';
import {initializeProjectIdentity} from '../src/project-identity.mjs';import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
const draft={version:1,revision:1,name:'Tender workspace',provider:'tools',nodes:[],edges:[],requirements:'Deadline is a business fact.'};
const t0=new Date('2026-11-19T00:00:00.000Z'),t1=new Date('2026-11-19T00:01:00.000Z'),t2=new Date('2026-11-19T01:00:00.000Z');
test('a new project keeps one identity and creation date through differently timed saves',()=>{
 const project=initializeProjectIdentity(draft,{now:t0,newId:()=> 'tender-fixture'}),before=structuredClone(project);
 const first=toProjectFile(project,t1),next=toProjectFile(project,t2);
 assert.equal(first.meta.id,next.meta.id);assert.equal(first.meta.createdAt,t0.toISOString());assert.equal(next.meta.createdAt,first.meta.createdAt);assert.notEqual(first.meta.updatedAt,next.meta.updatedAt);
 assert.deepEqual(project,before);assert.equal(draft.id,undefined);assert.equal(draft.createdAt,undefined);
});
test('legacy local drafts initialize missing metadata once and keep recorded business/source dates',()=>{
 const old={...draft,id:'legacy-tender',brief:{deadline:'2026-12-01T17:00:00Z'}};
 const migrated=initializeProjectIdentity(old,{now:t0,newId:()=>{throw Error('Must keep identity');}});
 const restored=initializeProjectIdentity(JSON.parse(JSON.stringify(migrated)),{now:t2});
 assert.equal(restored.createdAt,t0.toISOString());assert.deepEqual(restored.brief,old.brief);assert.equal(old.createdAt,undefined);
 const reopened=fromProjectFile(toProjectFile(restored,t2)).project;assert.equal(reopened.createdAt,t0.toISOString());
});
test('provided imported identity and date stay byte-for-byte unchanged',()=>{
 const imported={...draft,id:'owned-project',createdAt:'2020-03-04T12:00:00Z'};
 assert.equal(initializeProjectIdentity(imported,{now:t2}),imported);assert.equal(toProjectFile(imported,t2).meta.createdAt,imported.createdAt);
});
