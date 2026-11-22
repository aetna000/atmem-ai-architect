import test from 'node:test';import assert from 'node:assert/strict';
import {createPendingWork,pendingRequestLabel,trackedFetch} from '../src/pending-work.mjs';
test('concurrent actions retain waiting state until each action settles; finishing is idempotent',()=>{
 const store=createPendingWork();let changes=0;const unsubscribe=store.subscribe(()=>changes++);
 const a=store.begin('Saving…'),b=store.begin('Checking…');assert.equal(store.getSnapshot().length,2);
 a();a();assert.deepEqual(store.getSnapshot().map(w=>w.label),['Checking…']);b();assert.deepEqual(store.getSnapshot(),[]);assert.equal(changes,4);unsubscribe();store.begin('Another…');assert.equal(changes,4);
});
test('background observation stays quiet while user actions receive concrete waiting labels',()=>{
 for(const path of ['/api/architect/activity','/api/engineering/list','/api/engineering/events','/api/engineering/delivery','/api/engineering/recover','/api/engineering/validation/list','/api/cli-ready','/assets/app.js'])assert.equal(pendingRequestLabel(path),null,path);
 for(const path of ['/api/architect','/api/projects/list','/api/projects/save','/api/engineering/start','/api/engineering/download','/api/memory/overview'])assert.ok(pendingRequestLabel(path),path);
});
test('request feedback preserves the response, payload and cancellation signal',async()=>{
 const store=createPendingWork(),controller=new AbortController(),options={method:'POST',body:'unchanged',signal:controller.signal};let release;
 const response=new Response(JSON.stringify({saved:true})),fetcher=trackedFetch((input,init)=>{assert.equal(input,'/api/projects/save');assert.equal(init,options);return new Promise(resolve=>{release=()=>resolve(response);});},label=>store.begin(label));
 const waiting=fetcher('/api/projects/save',options);assert.equal(store.getSnapshot().length,1);release();assert.equal(await waiting,response);assert.deepEqual(await response.json(),{saved:true});assert.equal(store.getSnapshot().length,0);
});
test('failure and cancellation clear only their own waiting indicator',async()=>{
 const store=createPendingWork(),other=store.begin('Another action…'),failure=new DOMException('Stopped','AbortError');
 const fetcher=trackedFetch(async()=>{throw failure;},label=>store.begin(label));await assert.rejects(fetcher('/api/architect'),e=>e===failure);assert.equal(store.getSnapshot().length,1);other();assert.equal(store.getSnapshot().length,0);
});
test('observation requests never enter the pending-action lifecycle',async()=>{
 let begins=0;const response=new Response('{}'),fetcher=trackedFetch(async()=>response,()=>{begins++;return()=>{};});assert.equal(await fetcher('/api/engineering/events'),response);assert.equal(begins,0);
});
test('local asynchronous work clears its indicator when parsing or export fails',async()=>{
 const {withPendingWork,pendingWork}=await import('../src/pending-work.mjs');
 await assert.rejects(withPendingWork('Exporting…',async()=>{assert.equal(pendingWork.getSnapshot().length,1);throw Error('Fixture export failed');}),/Fixture export failed/);
 assert.equal(pendingWork.getSnapshot().length,0);
});
