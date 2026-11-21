import {readableDiagramFocus} from './diagram-focus.mjs';
import {movedDrawingCell} from './drawing-layout.mjs';
import {inspectDiagramReadability} from './diagram-readability.mjs';
import {installCanvasPan} from './canvas-pan.mjs';
import {DiagramReferences} from './DiagramReferences.jsx';
import React,{useEffect,useRef,useState} from 'react';
import {drawioRuntime} from './drawio-runtime.mjs';
import {installCanvasZoom} from './canvas-zoom.mjs';
import {populateDrawioGraph} from './drawio-render.mjs';
import './drawio-canvas.css';

const connectionIcon='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18"><circle cx="9" cy="9" r="8" fill="#f3a2b4" stroke="#873b50"/><path d="M9 5v8M5 9h8" stroke="#172033" stroke-width="1.5"/></svg>');

export function DrawioCanvas({graphRef,scene,selected,onSelect,onDoubleClick,onMove,onConnect,onRemove,onContext,
  onDropShape,onRename,onLayout,label,scopeLabel,layoutKey,autoFit=true}){
  const container=useRef(null),native=useRef(null),live=useRef(null);
  const [ready,setReady]=useState(false),[failure,setFailure]=useState(''),[referencesOpen,setReferencesOpen]=useState(false),[zoomPercent,setZoomPercent]=useState(100),[panMode,setPanMode]=useState(false),[layoutIssues,setLayoutIssues]=useState([]),[focusedId,setFocusedId]=useState('');
  live.current={scene,onSelect,onDoubleClick,onMove,onConnect,onRemove,onContext,onRename,onLayout,panMode,label,selected};
  const chosen=scene.vertices.find(v=>v.id===(Array.isArray(selected)?selected[0]:selected)&&v.selectable!==false);

  useEffect(()=>{
    let disposed=false,graph,disposeContext;
    drawioRuntime().then(mx=>{
      if(disposed)return;
      const element=container.current;
      graph=new mx.mxGraph(element);
      // AtMem owns grouping in the project model. Each native cell moves independently.
      graph.getCompositeParent=cell=>cell;
      graph.getReferenceTerminal=cell=>cell;
      const model=graph.getModel();
      const getCell=event=>event.getProperty('cell');
      const record=cell=>cell?.atmem;
      const handle=graph.connectionHandler;
      let updating=false,fitPending=autoFit,signature,suppressClickUntil=0,needsVisibleCheck=false;
      graph.setHtmlLabels(false);
      graph.setTooltips(false);
      graph.setCellsResizable(true);
      mx.mxVertexHandler.prototype.rotationEnabled=true;
      graph.setCellsCloneable(false);
      graph.setCellsDisconnectable(false);
      graph.setAllowDanglingEdges(false);
      graph.setPanning(false);
      graph.setGridSize(10);
      graph.graphHandler.guidesEnabled=true;
      graph.panningHandler.usePopupTrigger=false;
      graph.panningHandler.pinchEnabled=false;
      handle.connectImage=new mx.mxImage(connectionIcon,18,18);
      handle.getIconPosition=(icon,state)=>new mx.mxPoint(
        state.x+state.width-icon.bounds.width-6,state.getCenterY()-icon.bounds.height/2);
      graph.isCellMovable=cell=>Boolean((live.current.onLayout||live.current.onMove)&&model.isVertex(cell)&&(live.current.onLayout||record(cell)?.movable!==false)&&record(cell)?.selectable!==false);
      graph.isCellResizable=cell=>Boolean(live.current.onLayout&&model.isVertex(cell)&&record(cell)?.selectable!==false);
      graph.isCellRotatable=graph.isCellResizable;
      graph.isCellEditable=cell=>Boolean(live.current.onRename&&model.isVertex(cell)&&record(cell)?.selectable!==false);
      graph.isCellSelectable=cell=>Boolean(record(cell)&&record(cell).selectable!==false);
      graph.isCellConnectable=cell=>Boolean(live.current.onConnect&&model.isVertex(cell)&&record(cell)?.connectable!==false);
      graph.isValidSource=cell=>graph.isCellConnectable(cell)&&record(cell)?.canSend!==false;
      graph.isValidTarget=cell=>graph.isCellConnectable(cell)&&record(cell)?.canReceive!==false;
      graph.getEdgeValidationError=(_edge,source,target)=>{
        if(!graph.isValidSource(source)||!graph.isValidTarget(target)||source===target)return '';
        return null;
      };
      graph.labelChanged=(cell,value)=>{
        const item=record(cell);
        if(item)live.current.onRename?.(item.recordId||item.id,String(value));
        return cell;
      };
      graph.addListener(mx.mxEvent.CLICK,(_sender,event)=>{
        if(performance.now()<suppressClickUntil)return;
        const item=record(getCell(event));
        if(item?.selectable===false)return;
        if(item&&model.isEdge(getCell(event)))setReferencesOpen(true);
        live.current.onSelect?.(item?.recordId||item?.id,event.getProperty('event'));
      });
      graph.addListener(mx.mxEvent.DOUBLE_CLICK,(_sender,event)=>{
        const item=record(getCell(event));
        if(item&&live.current.onDoubleClick){
          event.consume();
          live.current.onDoubleClick(item.recordId||item.id);
        }
      });
      function persistLayout(changes){
        try{live.current.onLayout(changes);setFailure('');}catch(error){setFailure(error.message);}
        requestAnimationFrame(()=>{if(!disposed){signature=undefined;api.setScene(live.current.scene);api.select(live.current.selected);}});
      }
      graph.addListener(mx.mxEvent.CELLS_MOVED,(_sender,event)=>{
        if(updating)return;
        suppressClickUntil=performance.now()+150;
        const positions=event.getProperty('cells').filter(cell=>model.isVertex(cell)&&graph.isCellMovable(cell)).map(cell=>{
          const item=record(cell),point=model.getGeometry(cell);
          return movedDrawingCell(item,point,{absolute:!!live.current.onLayout});
        });
        if(positions.length){if(live.current.onLayout)persistLayout(positions);else live.current.onMove?.(positions);}
      });
      graph.addListener(mx.mxEvent.CELLS_RESIZED,(_sender,event)=>{
        if(updating||!live.current.onLayout)return;
        suppressClickUntil=performance.now()+150;
        persistLayout(event.getProperty('cells').filter(cell=>graph.isCellResizable(cell)).map(cell=>{
          const row=record(cell),g=model.getGeometry(cell);return{id:row.recordId||row.id,x:Math.round(g.x),y:Math.round(g.y),width:Math.max(40,Math.min(10000,Math.round(g.width))),height:Math.max(40,Math.min(10000,Math.round(g.height)))};
        }));
      });
      model.addListener(mx.mxEvent.CHANGE,(_sender,event)=>{
        if(updating||!live.current.onLayout)return;
        const changed=event.getProperty('edit')?.changes||[];
        const rotations=changed.filter(change=>change instanceof mx.mxStyleChange&&graph.isCellRotatable(change.cell)).flatMap(change=>{
          const row=record(change.cell),rotation=((Number(graph.getCellStyle(change.cell).rotation)||0)%360+360)%360;
          return rotation!==(row.rotation||0)?[{id:row.recordId||row.id,rotation:Math.round(rotation)%360}]:[];
        });
        if(rotations.length){suppressClickUntil=performance.now()+150;persistLayout(rotations);}
      });
      handle.addListener(mx.mxEvent.CONNECT,(_sender,event)=>{
        const wire=getCell(event),source=record(model.getTerminal(wire,true)),target=record(model.getTerminal(wire,false));
        // The React project accepts the change and sends the native graph its canonical edge ID.
        graph.removeCells([wire]);
        if(source&&target)live.current.onConnect?.(source.id,target.id);
      });
      const selectionId=()=>graph.getSelectionCells().map(cell=>record(cell)?.recordId||record(cell)?.id).filter(Boolean);
      const keys=event=>{
        if(/INPUT|TEXTAREA/.test(event.target.tagName))return;
        if(event.key==='Escape'){graph.clearSelection();live.current.onSelect?.(null);return;}
        const selected=selectionId();
        if(['Backspace','Delete'].includes(event.key)&&selected.length&&live.current.onRemove){
          event.preventDefault();
          live.current.onRemove(selected);
        }
      };
      const context=event=>{
        event.preventDefault();
        const at=api.position(event);
        const cell=graph.getCellAt(at.x*graph.view.scale+graph.view.translate.x*graph.view.scale,
          at.y*graph.view.scale+graph.view.translate.y*graph.view.scale);
        const item=record(cell);
        live.current.onContext?.(event,item?.recordId||item?.id);
      };
      const api={
        position(event){
          const rect=element.getBoundingClientRect(),{scale,translate}=graph.view;
          return {x:(event.clientX-rect.left+element.scrollLeft)/scale-translate.x,
            y:(event.clientY-rect.top+element.scrollTop)/scale-translate.y};
        },
        fit({nodes,padding=.12,maxZoom=1.2,minZoom=.1}={}){
          if(!element.clientWidth||!element.clientHeight)return false;
          const requested=nodes?.map(({id})=>model.getCell(id)).filter(Boolean);
          const rect=requested?.length?graph.getBoundingBox(requested):graph.getGraphBounds();
          const {scale}=graph.view;
          if(!rect?.width||!rect?.height)return false;
          const world={x:rect.x/scale-graph.view.translate.x,y:rect.y/scale-graph.view.translate.y,
            width:rect.width/scale,height:rect.height/scale};
          const width=element.clientWidth,height=element.clientHeight;
          const inset=(side,size)=>typeof padding==='number'?size*padding/(2*(1+padding)):
            Math.min(size*.4,Math.max(0,parseFloat(padding?.[side])||0));
          const left=inset('left',width),right=inset('right',width),top=inset('top',height),bottom=inset('bottom',height);
          const zoom=Math.max(minZoom,Math.min(maxZoom,(width-left-right)/world.width,(height-top-bottom)/world.height));
          // A readable initial view should contain a component, not the empty
          // centre of a large web of connectors. Explicit Fit remains global.
          const focus=!requested?.length&&minZoom>=1&&(world.width*zoom>width-left-right||world.height*zoom>height-top-bottom)
            ? readableDiagramFocus(live.current.scene,width-left-right,height-top-bottom,zoom):null;
          setFocusedId(requested?.length?requested[0].atmem.id:focus?.id||'');
          element.scrollLeft=0;element.scrollTop=0;
          graph.view.scaleAndTranslate(zoom,(width+left-right)/(2*zoom)-(focus?focus.x+focus.width/2:world.x+world.width/2),
            (height+top-bottom)/(2*zoom)-(focus?focus.y+focus.height/2:world.y+world.height/2));
          return true;
        },
        zoom(delta){
          const desired=Math.max(.10,Math.min(2.5,graph.view.scale+delta));
          graph.zoom(desired/graph.view.scale,true);
        },
        setScene(next){
          graph.setConnectable(Boolean(live.current.onConnect));
          const fingerprint=JSON.stringify(next);
          if(signature===fingerprint)return;
          signature=fingerprint;
          updating=true;
          let cells;
          try{cells=populateDrawioGraph(mx,graph,next);}
          finally{updating=false;}
          for(const cell of cells){
            const item=record(cell),shape=graph.view.getState(cell)?.shape?.node;
            if(!shape||!item||item.selectable===false)continue;
            shape.setAttribute('data-record-id',item.recordId||item.id);
            shape.setAttribute('data-cell-kind',model.isVertex(cell)?'vertex':'edge');
            shape.setAttribute('tabindex','0');
            shape.setAttribute('role','button');
            shape.setAttribute('aria-label',item.name||item.body);
            shape.addEventListener('keydown',event=>{
              if(event.key==='Enter'||event.key===' '){
                event.preventDefault();
                graph.setSelectionCell(cell);
                live.current.onSelect?.(item.recordId||item.id,event);
              }
            });
          }
          element.dataset.renderedPage=live.current.label;
          const checked=inspectDiagramReadability(graph,graph.atmemRenderedScene||next);needsVisibleCheck=!!checked.deferred;element.dataset.readabilityStatus=checked.deferred?'deferred':checked.passed?'passed':'failed';setLayoutIssues(checked.issues);
          if(fitPending&&next.vertices.length&&api.fit({minZoom:1}))fitPending=false;
        },
        select(ids){
          const wanted=Array.isArray(ids)?ids:ids?[ids]:[];
          const cells=graph.getChildCells(graph.getDefaultParent()).filter(cell=>{
            const row=record(cell);
            return row&&wanted.includes(row.recordId||row.id)&&row.selectable!==false;
          });
          graph.setSelectionCells(cells);
          for(const cell of cells){const handler=graph.selectionCellsHandler.getHandler(cell);for(const [i,sizer]of (handler?.sizers||[]).entries())sizer.node?.setAttribute('data-transform-handle',sizer===handler.rotationShape?'rotate':'resize-'+i);}
        },
      };
      const updateZoom=()=>setZoomPercent(Math.round(graph.view.scale*100));
      graph.view.addListener(mx.mxEvent.SCALE,updateZoom);
      graph.view.addListener(mx.mxEvent.SCALE_AND_TRANSLATE,updateZoom);
      native.current=api;
      if(graphRef)graphRef.current=api;
      const resize=new ResizeObserver(()=>{
        if(element.clientWidth&&element.clientHeight){if(needsVisibleCheck){needsVisibleCheck=false;signature=undefined;api.setScene(live.current.scene);api.select(live.current.selected);}else{graph.view.validate();const checked=inspectDiagramReadability(graph,graph.atmemRenderedScene||live.current.scene);element.dataset.readabilityStatus=checked.passed?'passed':'failed';setLayoutIssues(checked.issues);}}
        if(fitPending&&live.current.scene.vertices.length&&api.fit({minZoom:1}))fitPending=false;
      });
      resize.observe(element);
      const removeZoom=installCanvasZoom(element,graph);
      const removePan=installCanvasPan(element,graph,{isPanMode:()=>live.current.panMode,onBlankClick:()=>live.current.onSelect?.(null)});
      element.addEventListener('keydown',keys);
      element.addEventListener('contextmenu',context);
      disposeContext=()=>{
        resize.disconnect();
        removeZoom();
        removePan();
        element.removeEventListener('keydown',keys);
        element.removeEventListener('contextmenu',context);
      };
      setReady(true);
    }).catch(error=>{if(!disposed)setFailure(error.message);});
    return ()=>{
      disposed=true;
      disposeContext?.();
      graph?.destroy();
      if(graphRef)graphRef.current=null;
      native.current=null;
    };
  },[graphRef,autoFit]);
  useEffect(()=>{if(container.current)container.current.dataset.pan=panMode?'grab':'';},[panMode]);
  useEffect(()=>{if(ready)native.current?.setScene(scene);},[ready,scene]);
  useEffect(()=>{if(ready)native.current?.select(selected);},[ready,scene,selected]);

  return <div className="drawio-surface">
    {scopeLabel&&<div className="diagram-scope-label">{scopeLabel}</div>}
    <div ref={container} className="drawio-canvas" data-layout-key={layoutKey} tabIndex={0} aria-label={label}
      onDragOver={event=>{
        if(onDropShape&&event.dataTransfer.types.includes('application/atmem-shape')){
          event.preventDefault();event.stopPropagation();event.dataTransfer.dropEffect='copy';
        }
      }}
      onDrop={event=>{
        const shape=event.dataTransfer.getData('application/atmem-shape');
        if(shape&&onDropShape&&native.current){event.preventDefault();event.stopPropagation();onDropShape(shape,native.current.position(event));}
      }}/>
    {!!layoutIssues.length&&<div className="diagram-layout-issues" role="status">{layoutIssues.length} layout issues.<details><summary>Review affected elements</summary><ul>{layoutIssues.map((issue,i)=><li key={i}>{issue.kind.replaceAll('-',' ')} · {[...scene.vertices,...scene.wires].find(r=>r.id===issue.id)?.name||issue.id}</li>)}</ul></details>{onLayout&&<button type="button" onClick={()=>onLayout(null)}>Reset page layout</button>}</div>}
    {!!scene.vertices.length&&<div className="diagram-navigation">
      <button type="button" aria-label="Pan drawing" aria-pressed={panMode} onClick={()=>setPanMode(v=>!v)}>Pan</button>
      <label>Focus <select aria-label="Focus diagram element" value={focusedId} onChange={event=>{
        const id=event.target.value;if(!id)return;native.current?.fit({nodes:[{id}],minZoom:1,maxZoom:1});onSelect?.(id);
      }}><option value="">Find an element…</option>{scene.vertices.filter(v=>v.selectable!==false).map(v=><option key={v.id} value={v.id}>{v.name}</option>)}</select></label>
      {onLayout&&chosen&&<details className="diagram-transform"><summary>Size &amp; rotation</summary><form key={chosen.id+':'+chosen.width+':'+chosen.height+':'+chosen.rotation} onSubmit={event=>{
        event.preventDefault();const data=new FormData(event.currentTarget);try{onLayout([{id:chosen.id,width:Number(data.get('width')),height:Number(data.get('height')),rotation:Number(data.get('rotation'))}]);setFailure('');}catch(error){setFailure(error.message);}
      }}><label>Width<input aria-label="Element width" name="width" type="number" min="40" max="10000" defaultValue={Math.round(chosen.width)} required/></label><label>Height<input aria-label="Element height" name="height" type="number" min="40" max="10000" defaultValue={Math.round(chosen.height)} required/></label><label>Rotation<input aria-label="Element rotation" name="rotation" type="number" min="0" max="359" defaultValue={chosen.rotation||0} required/></label><button type="submit">Apply transform</button><button type="button" onClick={()=>onLayout(null)}>Reset page layout</button></form></details>}
      <button type="button" aria-label="Zoom out drawing" onClick={()=>native.current?.zoom(-.15)}>−</button><button type="button" aria-label="Fit drawing" onClick={()=>native.current?.fit()}>Fit</button><button type="button" aria-label="Zoom in drawing" onClick={()=>native.current?.zoom(.15)}>+</button>
      <button type="button" onClick={()=>native.current?.fit({minZoom:1,maxZoom:1})} aria-label="Read diagram at actual size">{zoomPercent<75?'Read labels · ':''}{zoomPercent}%</button>
    </div>}
    {!!scene.vertices.length&&<DiagramReferences scene={scene} selected={selected} onSelect={id=>{native.current?.select(id);onSelect?.(id);}} open={referencesOpen} onToggle={()=>setReferencesOpen(value=>!value)}/>}
    {failure&&<p role="alert" className="drawio-load-error">{failure}</p>}
  </div>;
}
