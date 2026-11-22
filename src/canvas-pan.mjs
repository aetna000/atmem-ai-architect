export function installCanvasPan(canvas,graph,{isPanMode=()=>false,onBlankClick,onSelectMany}={}){
 const controller=new AbortController(),options={capture:true,passive:false,signal:controller.signal};let space=false,drag=null,suppressClickUntil=0;
 const listen=(target,event,fn)=>target.addEventListener(event,fn,options);
 const input=n=>n?.closest?.('input,textarea,select,[contenteditable=true]');
 const cursor=()=>{canvas.dataset.pan=drag?'grabbing':space||isPanMode()?'grab':'';};
 listen(window,'keydown',e=>{if(e.code==='Space'&&!input(e.target)&&(canvas===document.activeElement||canvas.contains(document.activeElement))){e.preventDefault();space=true;cursor();}});
 listen(window,'keyup',e=>{if(e.code==='Space'){space=false;cursor();}});
 listen(window,'blur',()=>{space=false;drag?.box?.remove();drag=null;cursor();});
 listen(canvas,'pointerdown',e=>{
  if(e.pointerType==='touch'||input(e.target))return;
  const handle=graph.view.getOverlayPane()?.contains(e.target);
  const background=!handle&&!e.target.closest?.('[role=button],[data-cell-kind],[data-cell-label]');
  if(background&&e.button===0&&e.shiftKey&&!space&&!isPanMode()){
   e.preventDefault();e.stopImmediatePropagation();canvas.focus({preventScroll:true});
   const box=document.createElement('div');box.className='mxRubberband';box.style.pointerEvents='none';canvas.appendChild(box);
   drag={id:e.pointerId,x:e.clientX,y:e.clientY,selection:true,box};canvas.setPointerCapture(e.pointerId);return;
  }
  if(e.button!==1&&!(e.button===0&&(space||isPanMode()||background))){suppressClickUntil=0;return;}
  e.preventDefault();e.stopImmediatePropagation();canvas.focus({preventScroll:true});graph.escape();
  const {view}=graph;const x=view.translate.x-canvas.scrollLeft/view.scale,y=view.translate.y-canvas.scrollTop/view.scale;
  canvas.scrollLeft=0;canvas.scrollTop=0;view.scaleAndTranslate(view.scale,x,y);
  drag={id:e.pointerId,x:e.clientX,y:e.clientY,tx:x,ty:y,blank:background&&e.button===0&&!space&&!isPanMode()};canvas.setPointerCapture(e.pointerId);cursor();
 });
 listen(canvas,'pointermove',e=>{if(!drag||drag.id!==e.pointerId)return;e.preventDefault();e.stopImmediatePropagation();if(drag.selection){const r=canvas.getBoundingClientRect();Object.assign(drag.box.style,{left:Math.min(drag.x,e.clientX)-r.left+canvas.scrollLeft+'px',top:Math.min(drag.y,e.clientY)-r.top+canvas.scrollTop+'px',width:Math.abs(e.clientX-drag.x)+'px',height:Math.abs(e.clientY-drag.y)+'px'});return;}graph.view.scaleAndTranslate(graph.view.scale,drag.tx+(e.clientX-drag.x)/graph.view.scale,drag.ty+(e.clientY-drag.y)/graph.view.scale);});
 const stop=e=>{if(!drag||e.pointerId!==drag.id)return;if(drag.selection){
  const left=Math.min(drag.x,e.clientX),right=Math.max(drag.x,e.clientX),top=Math.min(drag.y,e.clientY),bottom=Math.max(drag.y,e.clientY),model=graph.getModel();
  const cells=model.filterDescendants(cell=>{if(!model.isVertex(cell)||!graph.isCellSelectable(cell))return false;const r=graph.view.getState(cell)?.shape?.node?.getBoundingClientRect();return r&&r.left>=left&&r.right<=right&&r.top>=top&&r.bottom<=bottom;});
  graph.setSelectionCells(cells);onSelectMany?.(cells.map(c=>c.atmem?.recordId||c.atmem?.id).filter(Boolean));drag.box.remove();
 }suppressClickUntil=performance.now()+350;e.preventDefault();e.stopImmediatePropagation();if(drag.blank&&Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<3)onBlankClick?.();if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);drag=null;cursor();};
 const suppress=e=>{if(performance.now()<suppressClickUntil){e.preventDefault();e.stopImmediatePropagation();}};
 listen(canvas,'click',suppress);listen(canvas,'dblclick',suppress);
 listen(canvas,'pointerup',stop);listen(canvas,'pointercancel',stop);listen(canvas,'lostpointercapture',()=>{drag?.box?.remove();drag=null;cursor();});
 return()=>{drag?.box?.remove();controller.abort();};
}
