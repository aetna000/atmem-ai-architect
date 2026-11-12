import test from 'node:test';import assert from 'node:assert/strict';
import {nextIntakeBatch,restoreQueuedMessages,restoreIntakePaused} from '../src/work-intake.mjs';import {withConversation,conversationMessages} from '../src/conversation.mjs';import {prefillAcceptedSettings} from '../src/engineering-defaults.mjs';
const item=(id,text,attachments=[])=>({id,projectId:'one',text,attachments});
test('queued updates combine in order and preserve separate project queues',()=>{
 const queue=[item('1','Build a site'),{...item('2','Other project'),projectId:'two'},item('3','Also keep project memory')];const batch=nextIntakeBatch(queue,'one');assert.deepEqual(batch.ids,['1','3']);assert.ok(batch.message.indexOf('Build a site')<batch.message.indexOf('Also keep project memory'));assert.equal(queue.length,3);
});
test('batch bounds split work without dropping text or attachment inputs',()=>{
 const queue=[item('1','a'.repeat(7900)),item('2','b'.repeat(7900))];assert.deepEqual(nextIntakeBatch(queue,'one').ids,['1']);const files=Array.from({length:4},(_,id)=>({id,data:'data'}));assert.deepEqual(nextIntakeBatch([item('1','First',files),item('2','Second',files)],'one').ids,['1']);assert.ok(nextIntakeBatch([item('1','Review file',[{name:'lost.png',originalNotSaved:true}])],'one').blocked);
});
test('legacy oversize and excess-file updates block without throwing or losing any intent',()=>{
 const text='A requirement. '.repeat(800),files=Array.from({length:5},(_,id)=>({id,data:'data'}));
 for(const invalid of [item('large',text),item('files','All these files matter',files)]){
  const queue=[invalid,item('later','Preserve my later correction')],before=structuredClone(queue);
  const blocked=nextIntakeBatch(queue,'one');assert.equal(blocked.blocked,invalid.id);assert.ok(blocked.reason);assert.deepEqual(queue,before);
  const validFirst=nextIntakeBatch([item('first','Start with this'),...queue],'one');assert.deepEqual(validFirst.ids,['first']);
 }
});
test('pending text intent survives project conversation saving; original files are not silently pretended available',()=>{
 const messages=[{role:'user',text:'Keep memory private',requestId:'request-1',workState:'queued'},{role:'user',text:'Use this drawing',requestId:'request-2',workState:'processing',attachments:[{id:'image',name:'diagram.png',mime:'image/png',data:'original'}]}];const p=withConversation({id:'one'},messages);assert.ok(!JSON.stringify(p).includes('original"'));const queue=restoreQueuedMessages(conversationMessages(p),'one');assert.equal(queue.length,2);assert.equal(queue[0].text,'Keep memory private');assert.deepEqual(nextIntakeBatch(queue,'one').ids,['request-1']);assert.ok(nextIntakeBatch(queue.slice(1),'one').blocked);
});
test('accepted engineering placement pre-fills blanks while preserving explicit and cross-cloud choices',()=>{
 const p={provider:'gcp',decisions:[{subject:'cloud.region',status:'Accepted',decision:'australia-southeast1'}],nodes:[{id:'a',data:{provider:'gcp',kind:'resource',origin:'proposed',config:{region:'To be selected'}}},{id:'b',data:{provider:'gcp',kind:'resource',origin:'proposed',config:{region:'us-central1'}}},{id:'c',data:{provider:'azure',kind:'resource',origin:'proposed',config:{region:'To be selected'}}}]};const next=prefillAcceptedSettings(p);assert.equal(next.nodes[0].data.config.region,'australia-southeast1');assert.equal(next.nodes[1].data.config.region,'us-central1');assert.equal(next.nodes[2].data.config.region,'To be selected');assert.equal(p.nodes[0].data.config.region,'To be selected');assert.equal(next.extensions.engineeringDefaults[0].basis,'User-accepted project cloud.region decision');assert.equal(prefillAcceptedSettings({...p,decisions:[]}).nodes[0].data.config.region,'To be selected');
});

test('an interrupted queue stays paused across a saved-conversation reload',()=>{
 const messages=[{role:'user',text:'First',requestId:'1',workState:'failed'},{role:'user',text:'Next',requestId:'2',workState:'queued'}];const reopened=conversationMessages(withConversation({id:'one'},messages));assert.equal(restoreIntakePaused(reopened),true);assert.equal(restoreIntakePaused([...reopened,{role:'user',text:'Recovered',workState:'complete'}]),false);
});
