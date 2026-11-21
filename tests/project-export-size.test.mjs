import test from 'node:test';import assert from 'node:assert/strict';
import {toProjectFile,parseProjectFile} from '../src/project-file.mjs';
import {deliveryPack} from '../src/delivery.mjs';

test('large project files reopen from pretty-printed downloads and Delivery',()=>{
 const date=new Date('2026-11-19T00:00:00Z'),records=Array.from({length:18000},(_,id)=>({id,a:true,b:false,c:null,d:1,e:2,f:3,g:4}));
 const project={id:'size-regression',createdAt:date.toISOString(),name:'History size regression',version:1,revision:1,provider:'tools',nodes:[],edges:[],needs:[],extensions:{records}};
 const download=JSON.stringify(toProjectFile(project,date),null,2);
 assert.ok(Buffer.byteLength(download)>2_000_000);
 assert.deepEqual(parseProjectFile(download).project.extensions.records,records);
 const recordsLarge=[...records,...records];
 const files=deliveryPack({...project,extensions:{records:recordsLarge}},null,'local',date),content=files['project.atmem-ai-architect.json'];
 assert.ok(Buffer.byteLength(content)>2_000_000);
 const reopened=parseProjectFile(content).project;assert.deepEqual(reopened.extensions.records,recordsLarge);assert.equal(reopened.id,project.id);assert.deepEqual(project.extensions.records,records);
});
