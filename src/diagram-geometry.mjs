// Clip against the open interior. A tangent along the border is not a crossing.
export function segmentCrossesRect(a,b,box,inset=0){
 const left=box.x+inset,right=box.x+box.width-inset,top=box.y+inset,bottom=box.y+box.height-inset;
 if(left>=right||top>=bottom)return false;
 if(Math.max(a.x,b.x)<=left||Math.min(a.x,b.x)>=right||Math.max(a.y,b.y)<=top||Math.min(a.y,b.y)>=bottom)return false;
 const dx=b.x-a.x,dy=b.y-a.y;let lo=0,hi=1;
 for(const [p,q]of [[-dx,a.x-left],[dx,right-a.x],[-dy,a.y-top],[dy,bottom-a.y]]){
  if(p===0){if(q<=0)return false;continue;}
  const t=q/p;if(p<0)lo=Math.max(lo,t);else hi=Math.min(hi,t);
  if(lo>=hi)return false;
 }
 return lo<hi;
}
