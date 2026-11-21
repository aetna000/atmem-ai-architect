export function installCanvasPan(canvas,graph,{isPanMode=()=>false,onBlankClick}={}){
 const controller=new AbortController(),options={capture:true,passive:false,signal:controller.signal};let space=false,drag=null;
 const listen=(target,event,fn)=>target.addEventListener(event,fn,options);
 const input=n=>n?.closest?.('input,textarea,select,[contenteditable=true]');
 const cursor=()=>{canvas.dataset.pan=drag?'grabbing':space||isPanMode()?'grab':'';};
 listen(window,'keydown',e=>{if(e.code==='Space'&&!input(e.target)&&(canvas===document.activeElement||canvas.contains(document.activeElement))){e.preventDefault();space=true;cursor();}});
 listen(window,'keyup',e=>{if(e.code==='Space'){space=false;cursor();}});
 listen(window,'blur',()=>{space=false;drag=null;cursor();});
 listen(canvas,'pointerdown',e=>{
  if(e.pointerType==='touch'||input(e.target))return;
  const handle=graph.view.getOverlayPane()?.contains(e.target);
  const background=!handle&&!e.target.closest?.('[role=button],[data-cell-kind],[data-cell-label]');
  if(e.button!==1&&!(e.button===0&&(space||isPanMode()||background)))return;
  e.preventDefault();e.stopImmediatePropagation();canvas.focus({preventScroll:true});graph.escape();
  const {view}=graph;const x=view.translate.x-canvas.scrollLeft/view.scale,y=view.translate.y-canvas.scrollTop/view.scale;
  canvas.scrollLeft=0;canvas.scrollTop=0;view.scaleAndTranslate(view.scale,x,y);
  drag={id:e.pointerId,x:e.clientX,y:e.clientY,tx:x,ty:y,blank:background&&e.button===0&&!space&&!isPanMode()};canvas.setPointerCapture(e.pointerId);cursor();
 });
 listen(canvas,'pointermove',e=>{if(!drag||drag.id!==e.pointerId)return;e.preventDefault();e.stopImmediatePropagation();graph.view.scaleAndTranslate(graph.view.scale,drag.tx+(e.clientX-drag.x)/graph.view.scale,drag.ty+(e.clientY-drag.y)/graph.view.scale);});
 const stop=e=>{if(!drag||e.pointerId!==drag.id)return;e.preventDefault();e.stopImmediatePropagation();if(drag.blank&&Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<3)onBlankClick?.();if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);drag=null;cursor();};
 listen(canvas,'pointerup',stop);listen(canvas,'pointercancel',stop);listen(canvas,'lostpointercapture',()=>{drag=null;cursor();});
 return()=>controller.abort();
}
