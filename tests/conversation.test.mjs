import test from 'node:test';
import assert from 'node:assert/strict';
import {conversationMessages,withConversation} from '../src/conversation.mjs';
import {toProjectFile,fromProjectFile} from '../src/project-file.mjs';
const emptyProject=()=>({id:crypto.randomUUID(),version:1,revision:1,name:'New project',provider:'tools',requirements:'',nodes:[],edges:[]});
test('conversation survives a project file round trip without changing design revision',()=>{
 const project={...emptyProject(),revision:7};
 const messages=[{role:'user',text:'Build a support assistant',attachments:[{id:'one',name:'diagram.png',mime:'image/png',data:'privatebytes'}]},{role:'assistant',text:'Which team will use it?'}];
 const saved=withConversation(project,messages);
 assert.equal(saved.revision,7);assert.equal(project.extensions?.conversation,undefined);
 const file=toProjectFile(saved);assert.ok(!JSON.stringify(file).includes('privatebytes'));
 const restored=conversationMessages(fromProjectFile(file).project);
 assert.equal(restored.length,2);assert.equal(restored[0].text,messages[0].text);assert.equal(restored[0].attachments[0].originalNotSaved,true);
 assert.deepEqual(conversationMessages(emptyProject(),[{role:'assistant',text:'Welcome'}]),[{role:'assistant',text:'Welcome'}]);
});
test('saved history is not truncated to the model context window and is isolated by project',()=>{
 const messages=Array.from({length:40},(_,i)=>({role:i%2?'assistant':'user',text:`Turn ${i}`}));
 const first=withConversation(emptyProject(),messages), second=withConversation(emptyProject(),[{role:'user',text:'Other project'}]);
 assert.equal(conversationMessages(first).length,40);assert.equal(conversationMessages(second)[0].text,'Other project');
 assert.notEqual(first.id,second.id);
});

test('public activity response association survives save without changing raw reply or exposing attachments',()=>{
 const activityId='00000000-0000-4000-8000-000000000001',messages=[{role:'assistant',text:'Exact reply',activityId}];assert.deepEqual(conversationMessages(withConversation(emptyProject(),messages)),messages);
});
