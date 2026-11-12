import React from 'react';
export function ChatResizeHandle({width,onChange}){
 const max=()=>Math.max(320,Math.min(900,window.innerWidth-360));
 const resize=value=>onChange(Math.round(Math.max(320,Math.min(max(),value))));
 return <div className="chat-resize-handle" role="separator" aria-label="Resize chat panel" aria-orientation="vertical" aria-valuemin={320} aria-valuemax={max()} aria-valuenow={width} tabIndex={0} title="Drag to resize chat. Arrow keys resize; double-click resets." onDoubleClick={()=>resize(360)} onKeyDown={e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();resize(e.key==='Home'?320:e.key==='End'?max():width+(e.key==='ArrowLeft'?32:-32));}}} onPointerDown={e=>{if(e.button!==0)return;e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);}} onPointerMove={e=>{if(e.currentTarget.hasPointerCapture(e.pointerId))resize(e.currentTarget.closest('.app').getBoundingClientRect().right-e.clientX);}} onPointerUp={e=>{if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);}}/>;
}
