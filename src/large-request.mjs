// Preserve the entire JSON payload; chunk transport changes no project content.
export async function postLargeJson(url,payload,{token,signal,onProgress,fetcher=fetch}={}){
 const data=new TextEncoder().encode(JSON.stringify(payload));
 if(data.length>64*1024*1024)throw Error('Project exceeds the 64 MiB validation upload limit.');
 const post=async(path,value,requestSignal=signal)=>{
  const response=await fetcher(path,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},body:JSON.stringify(value),signal:requestSignal});
  const result=await response.json();if(!response.ok)throw Error(result.detail||'Validation request could not start.');return result;
 };
 if(data.length<=192000)return post(url,payload);
 const sha256=[...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(x=>x.toString(16).padStart(2,'0')).join('');
 const {uploadId,chunkBytes}=await post('/api/terraform/uploads/start',{bytes:data.length,sha256});
 try{
  if(chunkBytes!==131072)throw Error('The upload service returned an unsupported chunk size.');
  for(let offset=0,index=0;offset<data.length;offset+=chunkBytes,index++){
   const chunk=data.subarray(offset,offset+chunkBytes);let text='';
   for(let i=0;i<chunk.length;i+=8192)text+=String.fromCharCode(...chunk.subarray(i,i+8192));
   await post('/api/terraform/uploads/chunk',{uploadId,index,data:btoa(text)});
   onProgress?.(Math.round(Math.min(offset+chunkBytes,data.length)/data.length*100));
  }
  onProgress?.(null);
  return await post(url+'-upload',{uploadId});
 }finally{
  await post('/api/terraform/uploads/cancel',{uploadId},AbortSignal.timeout(5000)).catch(()=>{});
 }
}
