import{test}from'node:test';import assert from'node:assert/strict';import{createHash}from'node:crypto';import{postLargeJson}from'../src/large-request.mjs';
test('large Unicode JSON is transmitted losslessly with progress and checksum',async()=>{
 const payload={project:{requirements:'🧠 preserve all requirements '.repeat(15000)},environment:'staging'},chunks=[];let header,validated=false,cancelled=false;const progress=[];
 const fetcher=async(url,options)=>{assert.equal(options.headers.Authorization,'Bearer fixture');assert(Buffer.byteLength(options.body)<250000);const p=JSON.parse(options.body);
 if(url.endsWith('/start')){header=p;return Response.json({uploadId:'fixture',chunkBytes:131072})}
 if(url.endsWith('/chunk')){assert.equal(p.index,chunks.length);chunks.push(Buffer.from(p.data,'base64'));return Response.json({})}
 if(url.endsWith('/cancel')){cancelled=true;return Response.json({})}
 assert.equal(url,'/api/terraform/validate-upload');const raw=Buffer.concat(chunks);assert.equal(raw.length,header.bytes);assert.equal(createHash('sha256').update(raw).digest('hex'),header.sha256);assert.deepEqual(JSON.parse(raw),payload);validated=true;return Response.json({status:'passed'});
 };
 assert.deepEqual(await postLargeJson('/api/terraform/validate',payload,{token:'fixture',fetcher,onProgress:p=>progress.push(p)}),{status:'passed'});assert(validated&&cancelled);assert(chunks.length>2);assert.equal(progress.at(-2),100);assert.equal(progress.at(-1),null);
});
test('small requests stay direct and a failed chunk never starts validation',async()=>{
 let paths=[];await postLargeJson('/api/terraform/validate',{project:{}},{fetcher:async url=>{paths.push(url);return Response.json({})}});assert.deepEqual(paths,['/api/terraform/validate']);paths=[];
 await assert.rejects(postLargeJson('/api/terraform/validate',{project:{requirements:'x'.repeat(300000)}},{fetcher:async url=>{paths.push(url);if(url.endsWith('/start'))return Response.json({uploadId:'fixture',chunkBytes:131072});if(url.endsWith('/cancel'))return Response.json({});return Response.json({detail:'Chunk rejected'},{status:422})}}),/Chunk rejected/);assert(!paths.includes('/api/terraform/validate-upload'));assert(paths.includes('/api/terraform/uploads/cancel'));
});
