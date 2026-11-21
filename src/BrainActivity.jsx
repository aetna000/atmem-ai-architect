import React,{useId} from 'react';
// Brain artwork supplied by the user. Crop the wordmark for legibility at icon size.
export function BrainActivity({size=24,active=true}){
 const mask=useId();
 return <svg className={`brain-activity${active?' is-active':''}`} width={size} height={size} viewBox="-150 -135 300 255" aria-hidden="true" focusable="false">
  <defs><mask id={mask} maskUnits="userSpaceOnUse" x="-200" y="-200" width="400" height="400"><rect x="-200" y="-200" width="400" height="400" fill="#fff"/>{[false,true].map(mirror=><path key={String(mirror)} d="M124 -31 Q98 -30 90 -54 M79 -88 Q72 -66 50 -60" transform={mirror?'scale(-1 1)':undefined} stroke="#000" strokeWidth="9" strokeLinecap="round" fill="none"/>)}</mask></defs>
  <g mask={`url(#${mask})`} fill="#F3A2B4">{[false,true].map(mirror=><path key={String(mirror)} d="M7 -104 A41.2 41.2 0 0 1 78.8 -87.95 A40.71 40.71 0 0 1 124.2 -31.16 A38 38 0 0 1 116.93 36.3 A42.22 42.22 0 0 1 60.09 85.83 A29.75 29.75 0 0 1 7 84 Z" transform={mirror?'scale(-1 1)':undefined}/>)}</g>
  {[-47,47].map(x=><g key={x}><circle cx={x} cy="26" r="35" fill="#F3F7F7" stroke="#101314" strokeWidth="12"/><circle cx={x+5} cy="21" r="10.5" fill="#101314"/></g>)}
  <path d="M-12 18 Q0 0 12 18" fill="none" stroke="#101314" strokeWidth="12" strokeLinecap="round"/>
 </svg>;
}
