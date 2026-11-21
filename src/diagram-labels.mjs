// Display projection only. Complete descriptions stay in records, details and exports.
// Explicit newlines are required: the native plain-SVG text renderer ignores CSS wrapping.
const glyphUnits=char=>char.codePointAt(0)>0x2ff?2:/[MW@#%]/.test(char)?1.7:/[A-Z]/.test(char)?1.2:1;
const units=value=>Array.from(value).reduce((sum,char)=>sum+glyphUnits(char),0);
export function wrapDiagramText(value,limit=34){
 const lines=[];
 for(const paragraph of String(value??'').split('\n')){
  let line='';
  for(const word of paragraph.split(/\s+/).filter(Boolean)){
   if(line&&units(line+' '+word)>limit){lines.push(line);line='';}
   let chunk='';
   for(const char of word){
    if(chunk&&units(chunk+char)>limit){if(line){lines.push(line);line='';}lines.push(chunk);chunk='';}
    chunk+=char;
   }
   if(chunk)line+=(line?' ':'')+chunk;
  }
  lines.push(line);
 }
 return lines;
}
export function compactNodeLabel(name,kind,{width=280,fields=[]}={}){
 const limit=Math.max(12,Math.floor((width-40)/8));
 const lines=[...wrapDiagramText(name,limit),...wrapDiagramText(kind,limit),...fields.flatMap(v=>wrapDiagramText(v,limit))].filter(Boolean);
 return{body:lines.join('\n'),width,height:Math.max(96,lines.length*19+38)};
}
export function numberConnections(scene){
 return{...scene,wires:scene.wires.map((row,index)=>({...row,reference:String(index+1),detailBody:row.detailBody??[row.mermaidLabel??row.body??row.name??'',...(row.record?.details||[]).map(d=>d.name+' · '+d.value)].filter(Boolean).join('\n'),body:String(index+1),style:row.style+'fontSize=13;fontStyle=1;spacing=4;'}))};
}
export function diagramReferenceRows(scene){
 const names=new Map(scene.vertices.map(v=>[v.id,v.name]));
 return scene.wires.map((row,index)=>({id:row.id,recordId:row.recordId||row.id,number:row.reference||String(index+1),
  from:names.get(row.source)||row.source,to:names.get(row.target)||row.target,
  description:row.detailBody??row.mermaidLabel??row.name??row.body,record:row.record}));
}
