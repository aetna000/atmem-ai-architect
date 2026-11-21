import test from 'node:test';
import assert from 'node:assert/strict';
import {copyProject} from '../src/project-copy.mjs';
test('copy preserves the original design and conversation without queued work or execution identities',()=>{
 const original={id:'source',revision:7,name:'Service',nodes:[{id:'api'}],needs:[{statement:'Keep the existing system'}],extensions:{architectureWork:{sessionId:'old'},architectureActivity:{turns:['old']},journey:{scope:'old'},conversation:{messages:[{role:'user',text:'My requirements',workState:'queued',requestId:'old'}]}}};
 const before=structuredClone(original),copy=copyProject(original,'new','2026-11-12');
 assert.deepEqual(original,before);assert.deepEqual(copy.nodes,original.nodes);assert.deepEqual(copy.needs,original.needs);
 assert.equal(copy.id,'new');assert.equal(copy.extensions.architectureWork,undefined);assert.equal(copy.extensions.journey,undefined);
 assert.equal(copy.extensions.conversation.messages[0].text,'My requirements');assert.equal(copy.extensions.conversation.messages[0].workState,undefined);
 assert.equal(copy.extensions.projectOrigin.projectId,'source');assert.throws(()=>copyProject(original,'source'));
});
