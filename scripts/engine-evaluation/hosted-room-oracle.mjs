// Independent acceptance for the explicitly labelled hosted generation fixture.
// Run only in the registered network-disabled container, never on the operator host.
import test from 'node:test';import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {once} from 'node:events';import {mkdtemp,rm} from 'node:fs/promises';
test('independent room reservation HTTP contract survives concurrency and restart',async()=>{
 const folder=await mkdtemp('/tmp/independent-rooms-');let process;
 async function launch(){
  process=spawn(globalThis.process.execPath,['server.mjs'],{env:{...globalThis.process.env,PORT:'0',DATA_FILE:folder+'/rooms.json'},stdio:['ignore','pipe','pipe']});
  return await new Promise((resolve,reject)=>{let text='';const timeout=setTimeout(()=>reject(Error('No listening address')),10000);process.stdout.on('data',bytes=>{text+=bytes;const found=text.match(/LISTENING (http:\/\/127\.0\.0\.1:\d+)/);if(found){clearTimeout(timeout);resolve(found[1]);}});process.once('error',reject);process.once('exit',code=>{clearTimeout(timeout);reject(Error('Server stopped '+code));});});
 }
 async function stop(){if(!process||process.exitCode!==null)return;const ended=once(process,'exit');process.kill('SIGTERM');await ended;}
 try{
  let url=await launch();const booking={room:'A',name:'Independent visitor',start:'2028-05-17T09:00:00Z',end:'2028-05-17T10:00:00Z'};
  const post=(body,headers={})=>fetch(url+'/api/reservations',{method:'POST',headers:{'Content-Type':'application/json',...headers},body:JSON.stringify(body)});
  const responses=await Promise.all(Array.from({length:8},()=>post(booking)));assert.equal(responses.filter(r=>r.status===201).length,1);assert.equal(responses.filter(r=>r.status===409).length,7);
  assert.equal((await post({...booking,room:'B'})).status,201);
  assert.equal((await post({...booking,start:booking.end,end:'2028-05-17T11:00:00Z'})).status,201);
  assert.equal((await post({...booking,name:''})).status,400);
  assert.equal((await post({...booking,start:booking.end,end:booking.start})).status,400);
  assert.equal((await post({...booking,room:'unknown'})).status,400);
  assert.equal((await post(booking,{Origin:'https://untrusted.invalid'})).status,403);
  assert.equal((await (await fetch(url+'/api/reservations')).json()).reservations.length,3);
  await stop();url=await launch();assert.equal((await (await fetch(url+'/api/reservations')).json()).reservations.length,3);
  assert.equal((await post(booking)).status,409);
 }finally{await stop();await rm(folder,{recursive:true,force:true});}
});
