import {useLayoutEffect,useRef} from 'react';

// Keep new messages inside their own viewport; never scroll the surrounding page.
export function useChatScroll(projectId,open){
 const viewport=useRef(null),content=useRef(null),resume=useRef(()=>{});
 useLayoutEffect(()=>{
  const pane=viewport.current,list=content.current;if(!pane||!list)return;
  let following=true,programmatic=false,frame=0;
  const atBottom=()=>pane.scrollHeight-pane.clientHeight-pane.scrollTop<=48;
  const move=(smooth=true)=>{
   if(!following)return;
   programmatic=true;
   pane.scrollTo({top:pane.scrollHeight,behavior:smooth&&!matchMedia('(prefers-reduced-motion: reduce)').matches?'smooth':'instant'});
  };
  // Layout/animation scroll events cannot opt out of following; user input can.
  const scroll=()=>{if(!programmatic)following=atBottom();};
  const interrupt=()=>{programmatic=false;};
  const wheel=e=>{interrupt();if(e.deltaY<0)following=false;};
  pane.addEventListener('scroll',scroll);
  pane.addEventListener('wheel',wheel,{passive:true});
  pane.addEventListener('touchstart',interrupt,{passive:true});
  pane.addEventListener('pointerdown',interrupt);
  pane.addEventListener('keydown',interrupt);
  move(false);
  const observer=new ResizeObserver(()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>move());});
  observer.observe(list);observer.observe(pane);
  resume.current=()=>{following=true;move();};
  return ()=>{
   observer.disconnect();cancelAnimationFrame(frame);resume.current=()=>{};
   pane.removeEventListener('scroll',scroll);
   pane.removeEventListener('wheel',wheel);pane.removeEventListener('touchstart',interrupt);
   pane.removeEventListener('pointerdown',interrupt);pane.removeEventListener('keydown',interrupt);
  };
 },[projectId,open]);
 return {viewport,content,followLatest:()=>resume.current()};
}
