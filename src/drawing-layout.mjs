import {fitDiagramFrames} from './diagram-frames.mjs';
import {routeDiagramWires} from './diagram-routing.mjs';
import {wrapDiagramText} from './diagram-labels.mjs';
export function validateDrawingLayouts(value){
 if(value===undefined)return;
 if(!value||value.version!==1||!value.pages||typeof value.pages!=='object'||Array.isArray(value.pages)||Object.keys(value.pages).length>600)throw Error('Invalid drawing layouts.');
 for(const [page,cells]of Object.entries(value.pages)){
  if(!page||page.length>240||!cells||typeof cells!=='object'||Array.isArray(cells)||Object.keys(cells).length>500)throw Error('Invalid drawing page layout.');
  for(const [id,cell]of Object.entries(cells)){
   if(!id||id.length>240||!cell||typeof cell!=='object'||Array.isArray(cell)||Object.keys(cell).some(k=>!['x','y','width','height','rotation'].includes(k)))throw Error('Invalid drawing geometry.');
   for(const [key,v]of Object.entries(cell))if(!Number.isFinite(v)||(['width','height'].includes(key)?v<40||v>10000:key==='rotation'?v<0||v>=360:Math.abs(v)>100000))throw Error('Drawing geometry is outside supported limits.');
  }
 }
}
export function updateDrawingLayout(layout,page,changes){
 if(changes===null){const pages={...layout?.pages};delete pages[page];return{version:1,pages};}
 const entries=new Map(Object.entries(layout?.pages?.[page]||{}));
 for(const {id,...geometry}of changes)entries.set(id,{...entries.get(id),...geometry});
 const cells=Object.fromEntries(entries);
 const next={version:1,pages:{...layout?.pages,[page]:cells}};validateDrawingLayouts(next);return next;
}
export function applyDrawingLayout(scene,cells){
 if(!cells||!Object.keys(cells).length)return scene;
 const vertices=scene.vertices.map(v=>{
  const edit=Object.hasOwn(cells,v.id)?cells[v.id]:null;if(!edit||v.selectable===false)return {...v};
  const size={...v,...edit},left=Number(v.style?.match(/(?:^|;)spacingLeft=([0-9.]+)/)?.[1]||20);
  const lines=edit.width!==undefined&&edit.width!==v.width?wrapDiagramText(v.name||v.body,Math.max(10,Math.floor((size.width-left-24)/8))):v.body.split('\n');
  return{...size,body:lines.join('\n'),style:v.style+'rotation='+(edit.rotation||0)+';'};
 });
 let wires=scene.wires;
 if(scene.timeline){
  const byId=new Map(vertices.map(v=>[v.id,v])),top=Math.max(165,...vertices.filter(v=>v.selectable!==false).map(v=>v.y+v.height+40)),bottom=top+(wires.length+1)*54;
  for(const v of vertices.filter(v=>v.id.startsWith('@lifeline-'))){const owner=byId.get(v.id.slice(10));if(owner){v.x=owner.x+owner.width/2;v.y=owner.y+owner.height;v.height=Math.max(1,bottom-v.y);}}
  wires=wires.map((w,i)=>{const a=byId.get(w.source),b=byId.get(w.target),y=top+i*54;return{...w,start:{x:a.x+a.width/2,y},end:{x:b.x+b.width/2,y:y+(a===b?20:0)},points:a===b?[{x:a.x+a.width/2+45,y},{x:a.x+a.width/2+45,y:y+20}]:undefined};});
 }
 return routeDiagramWires(fitDiagramFrames({...scene,vertices,wires}));
}
export function movedDrawingCell(row,point,{absolute=true}={}){
 return{id:row.recordId||row.id,x:Math.round(point.x-(absolute?0:row.offset?.x||0)),y:Math.round(point.y-(absolute?0:row.offset?.y||0))};
}
