import React,{useEffect,useSyncExternalStore} from 'react';
import {pendingWork,beginPendingWork} from './pending-work.mjs';
import './pending-feedback.css';
export function usePendingWork(label,active){
 useEffect(()=>{if(active)return beginPendingWork(label);},[label,Boolean(active)]);
}
export function PendingFeedback(){
 const work=useSyncExternalStore(pendingWork.subscribe,pendingWork.getSnapshot,pendingWork.getSnapshot);
 if(!work.length)return null;
 return <div className="pending-feedback" role="status" aria-live="polite" aria-atomic="true"><span className="pending-spinner" aria-hidden="true"/><span>{work.at(-1).label}</span></div>;
}
