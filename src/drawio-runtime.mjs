// Load the pinned graph engine distributed by draw.io into the application document.
import stencilXml from './drawing-stencils.xml?raw';
let ready;
let registered=false;
function registerShapes(mx){
  if(registered)return;
  const library=mx.mxUtils.parseXml(stencilXml).documentElement;
  for(const node of library.children)mx.mxStencilRegistry.addStencil(node.getAttribute('id'),new mx.mxStencil(node));
  registered=true;
  const add=(name,path,details='')=>{
    if(mx.mxStencilRegistry.getStencil(name))return;
    const outline='<path>'+path+'</path><fillstroke/>';
    const xml='<shape w="100" h="100" aspect="variable" strokewidth="inherit"><background>'+outline+
      '</background><foreground>'+details+'</foreground></shape>';
    mx.mxStencilRegistry.addStencil(name,new mx.mxStencil(mx.mxUtils.parseXml(xml).documentElement));
  };
  add('parallelogram','<move x="18" y="0"/><line x="100" y="0"/><line x="82" y="100"/><line x="0" y="100"/><close/>');
  add('note','<move x="0" y="0"/><line x="82" y="0"/><line x="100" y="24"/><line x="100" y="100"/><line x="0" y="100"/><close/>',
    '<path><move x="82" y="0"/><line x="82" y="24"/><line x="100" y="24"/></path><stroke/>');
}
function brand(mx){
  const rose='#873b50',pink='#f3a2b4';
  registerShapes(mx);
  Object.assign(mx.mxConstants,{VERTEX_SELECTION_COLOR:rose,EDGE_SELECTION_COLOR:rose,HIGHLIGHT_COLOR:pink,VALID_COLOR:rose,
    OUTLINE_HIGHLIGHT_COLOR:rose,CONNECT_TARGET_COLOR:rose,DROP_TARGET_COLOR:rose,GUIDE_COLOR:pink,
    HANDLE_FILLCOLOR:pink,HANDLE_STROKECOLOR:rose,CONNECT_HANDLE_FILLCOLOR:pink,
    LABEL_HANDLE_FILLCOLOR:pink,OUTLINE_HANDLE_FILLCOLOR:pink,OUTLINE_HANDLE_STROKECOLOR:rose});
  return mx;
}
export function drawioRuntime(){
  if(window.mxGraph)return Promise.resolve(brand(window));
  if(!ready)ready=new Promise((resolve,reject)=>{
    const base=`${import.meta.env.BASE_URL}drawio`;
    Object.assign(window,{mxBasePath:base,mxImageBasePath:base+'/images',mxLoadResources:false,mxLoadStylesheets:false});
    const script=document.createElement('script');
    script.src=base+'/mxClient.js';
    script.onload=()=>window.mxGraph?resolve(brand(window)):reject(Error('The diagram editor did not start.'));
    script.onerror=()=>reject(Error('The diagram editor could not be loaded.'));
    document.head.append(script);
  }).catch(error=>{ready=null;throw error;});
  return ready;
}
