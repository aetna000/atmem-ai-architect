import{unzipSync,zipSync,strToU8,strFromU8}from'fflate';
const safe=name=>name&&!name.startsWith('/')&&!name.includes('\\')&&!name.split('/').some(p=>p==='..'||p==='.')&&!name.includes('\0');
function attributes(bytes){
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);let end=bytes.length-22;
 while(end>=Math.max(0,bytes.length-65557)&&view.getUint32(end,true)!==0x06054b50)end--;
 if(end<0||end+22+view.getUint16(end+20,true)!==bytes.length||view.getUint16(end+4,true)||view.getUint16(end+6,true))throw Error('Unsupported package directory.');
 const result=new Map(),count=view.getUint16(end+10,true);let offset=view.getUint32(end+16,true);
 for(let i=0;i<count;i++){
  if(offset+46>end||view.getUint32(offset,true)!==0x02014b50)throw Error('Invalid package directory.');
  const length=view.getUint16(offset+28,true),extra=view.getUint16(offset+30,true),comment=view.getUint16(offset+32,true);
  if(offset+46+length+extra+comment>end)throw Error('Invalid package entry.');
  const name=strFromU8(bytes.subarray(offset+46,offset+46+length));if(!safe(name)||result.has(name))throw Error('Unsafe or duplicate package entry.');
  result.set(name,{os:view.getUint16(offset+4,true)>>>8,attrs:view.getUint32(offset+38,true)});offset+=46+length+extra+comment;
 }
 if(offset!==end)throw Error('Package directory does not match its receipt.');return result;
}
export async function completeProjectZip(verified,design){
 if(!design?.files)throw Error('Wait for the design documents to finish preparing.');
 const bytes=new Uint8Array(await verified.arrayBuffer()),attrs=attributes(bytes);let expanded=0;
 const original=unzipSync(bytes,{filter:entry=>{expanded+=entry.originalSize;if(expanded>150000000)throw Error('Package exceeds its receiving limit.');return true;}});
 const output=Object.fromEntries(Object.entries(original).map(([name,data])=>[name,[data,attrs.get(name)]]));
 const documents={};for(const[name,value]of Object.entries(design.files)){
  if(!safe(name))throw Error('Invalid design document path.');
  const target='design-documents/'+name;if(output[target])throw Error('Design documents conflict with captured files.');
  const content=typeof value==='string'?strToU8(value):value;expanded+=content.byteLength;if(expanded>150000000)throw Error('Combined package exceeds its receiving limit.');
  output[target]=[content,{os:3,attrs:0o100644<<16}];documents[target]=content;
 }
 const hash=async data=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(b=>b.toString(16).padStart(2,'0')).join('');
 const manifest={version:1,designRevision:design.manifest.designRevision,sourceArtifactPreserved:'evidence/original-implementation.zip',documents:await Promise.all(Object.entries(documents).map(async([path,data])=>({path,bytes:data.byteLength,sha256:await hash(data)})))};
 output['package-contents.json']=strToU8(JSON.stringify(manifest,null,2));
 const readme=strFromU8(original['START_HERE.md']||new Uint8Array());
 output['START_HERE.md']=strToU8('# Open this project\n\nUnzip this package, then open this folder as a project in Orca or your editor. Read this file and the implementation README before running commands.\n\n- implementation/: captured application, infrastructure and tests.\n- design-documents/: requirements, Spec Kit, diagram, cost assumptions and generated design references.\n- evidence/: captured source ZIP and recorded checks.\n\nDesign references are not proof that changed requirements were implemented.\n\n'+readme);
 return new Blob([zipSync(output)],{type:'application/zip'});
}
