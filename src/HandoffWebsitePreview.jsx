import React,{useEffect,useRef,useState} from 'react';

const mime={html:'text/html',css:'text/css',svg:'image/svg+xml',png:'image/png',jpg:'image/jpeg',gif:'image/gif',webp:'image/webp',pdf:'application/pdf',zip:'application/zip'};

// Resolve only files in the generated team package. The iframe cannot run
// scripts, submit forms or navigate its parent, including from an authored guide.
export function HandoffWebsitePreview({files,revision,snapshotChanged,onClose}){
  const dialog=useRef(null),frame=useRef(null);
  const [location,setLocation]=useState({path:'index.html',hash:''});
  useEffect(()=>{const node=dialog.current;node.showModal();return()=>node.close();},[]);
  useEffect(()=>{
    const iframe=frame.current,urls=new Map(),origin='https://handoff.invalid/';
    const urlFor=name=>{
      if(!urls.has(name))urls.set(name,URL.createObjectURL(new Blob([files[name]],{type:mime[name.split('.').at(-1)]||'application/octet-stream'})));
      return urls.get(name);
    };
    const resolve=href=>new URL(href,origin+location.path);
    const source=files[location.path].replace(/(<(?:img|source|link)\b[^>]*?\s(?:src|srcset|href)=")([^"]+)"/gi,(tag,prefix,src)=>{
      const url=resolve(src),file=decodeURIComponent(url.pathname.slice(1));
      return url.origin==='https://handoff.invalid'&&Object.hasOwn(files,file)?prefix+urlFor(file)+'"':tag;
    }).replace("img-src 'self' data:","img-src 'self' data: blob:")
      .replace("style-src 'self'","style-src 'self' blob:");
    const content=URL.createObjectURL(new Blob([source],{type:'text/html'}));
    function follow(event){
      const a=event.target.closest('a[href]');if(!a)return;
      const href=a.getAttribute('href');
      if(href.startsWith('#'))return;
      event.preventDefault();
      const url=resolve(href);
      if(url.origin!=='https://handoff.invalid'){
        if(['http:','https:'].includes(url.protocol))window.open(url.href,'_blank','noopener,noreferrer');
        return;
      }
      const name=decodeURIComponent(url.pathname.slice(1));
      if(!Object.hasOwn(files,name))return;
      if(name.endsWith('.html')){setLocation({path:name,hash:url.hash});return;}
      const dl=document.createElement('a');dl.href=urlFor(name);dl.download=name.split('/').at(-1);dl.click();
    }
    function ready(){iframe.contentDocument?.addEventListener('click',follow);}
    iframe.addEventListener('load',ready);iframe.src=content+location.hash;
    return()=>{iframe.removeEventListener('load',ready);iframe.contentDocument?.removeEventListener('click',follow);URL.revokeObjectURL(content);for(const url of urls.values())URL.revokeObjectURL(url);};
  },[files,location]);
  return <dialog ref={dialog} className="handoff-reader-dialog" aria-label="Handoff website" onCancel={onClose}>
    <header><strong>Handoff preview · revision {revision}</strong>{snapshotChanged&&<span role="status">The project changed. Reopen for the current snapshot.</span>}<button className="btn" autoFocus onClick={onClose}>Close preview</button></header>
    <iframe ref={frame} sandbox="allow-same-origin" title="Handoff website pages"/>
  </dialog>;
}
