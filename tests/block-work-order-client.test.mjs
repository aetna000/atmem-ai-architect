import test from'node:test';import assert from'node:assert/strict';
import{pendingBlockOrder,loadBlockOrder,saveBlockOrder,blockOrderPayload,verifyBlockOrderAcceptance,blockOrderKey}from'../src/block-work-order-client.mjs';
const session='00000000-0000-0000-0000-000000000001',request='00000000-0000-0000-0000-000000000002';
function storage(){const data=new Map();return{getItem:key=>data.get(key)||null,setItem:(key,value)=>data.set(key,value),removeItem:key=>data.delete(key)};}
test('block retry retains exact scope and digest across reload, without browser-generated instructions',()=>{
 const store=storage(),order=pendingBlockOrder('project-library',session,'loan-ledger','a'.repeat(64),request);saveBlockOrder(store,order.projectId,order);
 const restored=loadBlockOrder(store,order.projectId);assert.equal(restored.error,'');assert.deepEqual(restored.pending,order);
 assert.deepEqual(blockOrderPayload(restored.pending),{projectId:order.projectId,sessionId:session,requestId:request,blockId:'loan-ledger',contextSha256:'a'.repeat(64)});
 assert.equal('text'in blockOrderPayload(order),false);assert.equal(loadBlockOrder(store,'other-project').pending,null);
});
test('only matching accepted run, block and immutable basis can clear a retained request',()=>{
 const order=pendingBlockOrder('project-awards',session,'award-review','a'.repeat(64),request);
 const result={acceptedRunId:request,workOrder:{kind:'build_block',blockId:'award-review',contextSha256:'a'.repeat(64)}};
 assert.equal(verifyBlockOrderAcceptance(order,result),result);
 for(const wrong of [{...result,acceptedRunId:session},{...result,workOrder:{...result.workOrder,blockId:'another'}},{...result,workOrder:{...result.workOrder,contextSha256:'b'.repeat(64)}}])assert.throws(()=>verifyBlockOrderAcceptance(order,wrong));
});
test('unreadable and cross-project saved requests remain available for inspection',()=>{
 const store=storage();store.setItem(blockOrderKey('project-library'),'broken');assert.match(loadBlockOrder(store,'project-library').error,/could not be read/);assert.equal(store.getItem(blockOrderKey('project-library')),'broken');
 assert.throws(()=>saveBlockOrder(store,'other-project',pendingBlockOrder('project-library',session,'loans','a'.repeat(64),request)));
});
test('unavailable browser storage prevents submission persistence explicitly',()=>{
 assert.throws(()=>saveBlockOrder({setItem(){throw Error('quota');}},'project-library',pendingBlockOrder('project-library',session,'loans','a'.repeat(64),request)),/quota/);
});
