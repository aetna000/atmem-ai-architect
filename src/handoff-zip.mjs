import {strToU8,zipSync} from 'fflate';

// Preserve file attributes supplied by captured workspaces. Large archives
// compress off the browser thread so preparation feedback stays responsive.
export async function compressZipEntries(entries){
  const values=Object.values(entries);
  const size=values.reduce((sum,value)=>sum+(Array.isArray(value)?value[0]:value).byteLength,0);
  if(typeof Worker==='undefined'||(values.length<100&&size<512*1024))return zipSync(entries);
  const worker=new Worker(new URL('./handoff-zip.worker.mjs',import.meta.url),{type:'module'});
  try{
    return await new Promise((resolve,reject)=>{
      worker.onmessage=({data})=>data.error?reject(Error(data.error)):resolve(data.bytes);
      worker.onerror=event=>reject(Error(event.message||'Could not prepare the handoff ZIP.'));
      worker.postMessage(entries);
    });
  }finally{worker.terminate();}
}
export function zipFiles(files){
  const entries=Object.fromEntries(Object.entries(files).map(([name,body])=>{
    const bytes=typeof body==='string'?strToU8(body):body;
    return [name,/\.(zip|png|jpg|jpeg|webp|gif)$/i.test(name)?[bytes,{level:0}]:bytes];
  }));
  return compressZipEntries(entries);
}
