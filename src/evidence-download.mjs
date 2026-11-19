// Bound decoded bytes while streaming; a small Content-Length cannot bypass the cap.
export async function readBoundedEvidence(response,maxBytes,label='Evidence'){
 const declared=response.headers.get('content-length');
 if(declared!==null&&(!/^\d+$/.test(declared)||Number(declared)>maxBytes))throw Error(`${label} exceeds its byte bound.`);
 const reader=response.body?.getReader();if(!reader)throw Error(`${label} has no body.`);
 const chunks=[];let length=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>maxBytes)throw Error(`${label} exceeds its byte bound.`);chunks.push(value);}}
 catch(error){await reader.cancel().catch(()=>{});throw error;}finally{reader.releaseLock();}
 const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}return bytes;
}
