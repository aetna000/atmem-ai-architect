export const ATTACHMENT_ACCEPT='.png,.jpg,.jpeg,.webp,.pdf,.docx,.txt,.md,.csv,.json,.drawio,.xml';
const types={png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg',webp:'image/webp',pdf:'application/pdf',docx:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',txt:'text/plain',md:'text/markdown',csv:'text/csv',json:'application/json',drawio:'text/plain',xml:'text/plain'};
export async function readAttachments(files,existing=[]){
 if(files.length+existing.length>4)throw Error('Attach up to four files per message.');
 if([...existing,...files].reduce((n,f)=>n+f.size,0)>8*1024*1024)throw Error('Keep all attachments together below 8 MB.');
 return Promise.all([...files].map(async file=>{
  const mime=types[file.name.split('.').pop().toLowerCase()]||(['image/png','image/jpeg','image/webp'].includes(file.type)?file.type:null);
  if(!mime)throw Error(`${file.name}: use PNG, JPEG, WebP, PDF, DOCX, TXT, Markdown, CSV, JSON or draw.io.`);
  if(!file.size||file.size>4*1024*1024)throw Error(`${file.name}: each file must be between 1 byte and 4 MB.`);
  const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error(`Could not read ${file.name}.`));reader.readAsDataURL(file);});
  return {id:crypto.randomUUID(),name:file.name.replace(/[\/\\\x00-\x1f]/g,'_').slice(0,180),mime,data,size:file.size};
 }));
}
