import React,{useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
export function DrawingGroupDialog({initial,onSave,onClose}){
 const dialog=useRef(null),[name,setName]=useState(initial||''),[error,setError]=useState('');
 useEffect(()=>{dialog.current.showModal();},[]);
 return createPortal(<dialog className="drawing-group-dialog architecture-dialog" aria-label={initial?'Rename group':'Group selection'} ref={dialog} onCancel={e=>{e.preventDefault();onClose();}}>
  <form onSubmit={e=>{e.preventDefault();try{onSave(name);}catch(failure){setError(failure.message);}}}>
   <h3>{initial?'Rename group':'Group selection'}</h3><label>Group name<input aria-label="Group name" maxLength={150} required autoFocus value={name} onChange={e=>setName(e.target.value)}/></label>
   {error&&<p role="alert">{error}</p>}<footer><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn primary">{initial?'Save name':'Create group'}</button></footer>
  </form>
 </dialog>,document.body);
}
