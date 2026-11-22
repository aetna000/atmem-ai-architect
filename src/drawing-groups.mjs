import {containerDescendants} from './drawing-containment.mjs';
import {wrapDiagramText} from './diagram-labels.mjs';
export const visualGroupPrefix='@visual-group-';
export function validateDrawingGroups(pages){
 if(pages===undefined)return;
 if(!pages||typeof pages!=='object'||Array.isArray(pages)||Object.keys(pages).length>600)throw Error('Invalid drawing groups.');
 for(const [page,groups]of Object.entries(pages)){
  if(!page||page.length>240||!Array.isArray(groups)||groups.length>500)throw Error('Invalid drawing groups.');
  const byId=new Map(),owners=new Map();
  for(const g of groups){
   if(!g||Object.keys(g).some(k=>!['id','name','memberIds'].includes(k))||typeof g.id!=='string'||!g.id.startsWith(visualGroupPrefix)||g.id.length>240||byId.has(g.id)||typeof g.name!=='string'||!g.name.trim()||g.name.length>150||!Array.isArray(g.memberIds)||g.memberIds.length>500||new Set(g.memberIds).size!==g.memberIds.length)throw Error('Invalid drawing group.');
   byId.set(g.id,g);
   for(const id of g.memberIds){if(typeof id!=='string'||!id||id.length>240||owners.has(id))throw Error('An element can belong to one visual group at a time.');owners.set(id,g.id);}
  }
  for(const g of groups){const seen=new Set([g.id]);for(let id=owners.get(g.id);id;id=owners.get(id)){if(seen.has(id))throw Error('Visual groups cannot contain a cycle.');seen.add(id);}}
 }
}
export function updateDrawingGroups(layout,page,groups,options={}){
 const retained=new Set(groups.map(g=>g.id)),pages={...layout?.pages};
 if(pages[page])pages[page]=Object.fromEntries(Object.entries(pages[page]).filter(([id])=>!id.startsWith(visualGroupPrefix)||retained.has(id)));
 const parents={...layout?.parents?.[page]};
 for(const old of layout?.groups?.[page]||[])if(!retained.has(old.id)){for(const member of old.memberIds)if(parents[member]===old.id)parents[member]=parents[old.id]||null;delete parents[old.id];}
 for(const g of groups)for(const member of g.memberIds)parents[member]=g.id;
 Object.assign(parents,options.parents);
 const next={...layout,version:1,pages,parents:{...layout?.parents,[page]:parents},groups:{...layout?.groups,[page]:groups}};validateDrawingGroups(next.groups);return next;
}
export function createDrawingGroup(groups,scene,ids,name,id=visualGroupPrefix+crypto.randomUUID()){
 const byId=new Map(scene.vertices.filter(v=>v.selectable!==false).map(v=>[v.id,v]));
 const selected=new Set(ids);if(selected.size<2||[...selected].some(id=>!byId.has(id)))throw Error('Select at least two elements.');
 // Selecting a container already includes its descendants; do not assign them twice.
 const members=[...selected].filter(id=>{const seen=new Set();for(let p=byId.get(id)?.containerParentId;p&&!seen.has(p);p=byId.get(p)?.containerParentId){if(selected.has(p))return false;seen.add(p);}return true;});
 if(members.length<2)throw Error('Select at least two independent elements.');
 const roots=new Set(members),owners=members.map(member=>(groups||[]).find(g=>g.memberIds.includes(member))?.id),parent=owners[0]&&owners.every(owner=>owner===owners[0])?owners[0]:null;
 const next=[...(groups||[]).map(g=>({...g,memberIds:[...g.memberIds.filter(member=>!roots.has(member)),...(g.id===parent?[id]:[])]})).filter(g=>g.memberIds.length),{id,name:name.trim(),memberIds:members}];validateDrawingGroups({page:next});return{groups:next,id};
}
export function ungroupDrawing(groups,id){
 const group=groups.find(g=>g.id===id);if(!group)return groups;
 const next=groups.filter(g=>g.id!==id).map(g=>({...g,memberIds:g.memberIds.flatMap(member=>member===id?group.memberIds:[member])}));validateDrawingGroups({page:next});return next;
}
// Visual groups never change component ownership, record IDs, specs or interfaces.
export function applyDrawingGroups(scene,groups,cells,overrides){
 if(!groups?.length)return scene;
 validateDrawingGroups({page:groups});
 const rows=scene.vertices.map(v=>({...v})),byId=new Map(rows.map(v=>[v.id,v])),specs=new Map(groups.map(g=>[g.id,g]));
 if(groups.some(g=>byId.has(g.id)))throw Error('A visual group ID conflicts with an element.');
 function make(id){
  if(byId.has(id))return byId.get(id);
  const group=specs.get(id);if(!group)return;
  const members=group.memberIds.map(id=>byId.get(id)||make(id)).filter(Boolean),stored=cells?.[id];
  if(!members.length){const row={id,name:group.name,body:group.name,visualGroup:true,container:true,selectable:true,connectable:false,headerHeight:48,x:stored?.x??40,y:stored?.y??40,width:stored?.width||360,height:stored?.height||240,style:'shape=swimlane;startSize=48;rounded=1;fillColor=#faeaf0;swimlaneFillColor=none;strokeColor=#873b50;'};byId.set(id,row);rows.push(row);return row;}
  const parents=[...new Set(members.map(v=>overrides&&Object.hasOwn(overrides,v.id)&&overrides[v.id]!==id?overrides[v.id]||undefined:v.containerParentId))];const parent=overrides&&Object.hasOwn(overrides,id)?overrides[id]||undefined:parents.length===1?parents[0]:undefined;
  const x=stored?.x??Math.min(...members.map(v=>v.x))-24;
  const width=stored?.width||Math.max(180,Math.max(...members.map(v=>v.x+v.width))-x+24);
  const title=wrapDiagramText(group.name,Math.max(12,Math.floor((width-40)/8)));
  const headerHeight=Math.max(48,title.length*19+16);let y=stored?.y??Math.min(...members.map(v=>v.y))-headerHeight-28;
  const owner=byId.get(parent),minimum=owner?owner.y+(owner.headerHeight||48)+20:y;
  if(y<minimum){const dy=minimum-y,moved=new Set();for(const member of members)for(const v of [member,...containerDescendants([...byId.values()],member.id)])if(!moved.has(v.id)){v.y+=dy;moved.add(v.id);}y=minimum;}
  const height=stored?.height||Math.max(...members.map(v=>v.y+v.height))-y+24;
  const row={id,name:group.name,body:title.join('\n'),detailBody:group.name,visualGroup:true,container:true,containerParentId:parent,headerHeight:Math.max(48,title.length*19+16),x,y,width,height,selectable:true,connectable:false,
   style:'shape=swimlane;rounded=1;startSize='+Math.max(48,title.length*19+16)+';horizontal=1;whiteSpace=wrap;html=0;overflow=hidden;fontSize=14;align=left;spacingLeft=16;fillColor=#faeaf0;swimlaneFillColor=none;strokeColor=#873b50;fontColor=#172033;'};
  byId.set(id,row);rows.push(row);for(const member of members)member.containerParentId=id;return row;
 }
 groups.forEach(g=>make(g.id));
 // Native parents must exist before their children are inserted.
 const sorted=[],visited=new Set();function insert(v){if(visited.has(v.id))return;visited.add(v.id);const p=byId.get(v.containerParentId);if(p)insert(p);sorted.push(v);}
 rows.forEach(insert);return{...scene,vertices:sorted};
}
