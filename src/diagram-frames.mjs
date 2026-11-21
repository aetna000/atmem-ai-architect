// Group membership is semantic; frame bounds follow the displayed member geometry.
export function fitDiagramFrames(scene){
 const byId=new Map(scene.vertices.map(v=>[v.id,v]));
 return{...scene,vertices:scene.vertices.map(frame=>{
  if(!frame.memberIds)return frame;
  const members=frame.memberIds.map(id=>byId.get(id)).filter(Boolean).map(v=>{const angle=(v.rotation||0)*Math.PI/180,c=Math.abs(Math.cos(angle)),s=Math.abs(Math.sin(angle)),width=v.width*c+v.height*s,height=v.width*s+v.height*c;return{x:v.x+v.width/2-width/2,y:v.y+v.height/2-height/2,width,height};});if(!members.length)return frame;
  const x=Math.min(...members.map(v=>v.x))-24,y=Math.min(...members.map(v=>v.y))-24;
  return{...frame,x,y,width:Math.max(...members.map(v=>v.x+v.width))-x+24,height:Math.max(...members.map(v=>v.y+v.height))-y+24};
 })};
}
