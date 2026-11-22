import {usePendingWork} from './PendingFeedback.jsx';
import {updateDrawingLayout} from './drawing-layout.mjs';
import {arrangeDrawingScene,arrangementChanges,layoutConflictScore} from './drawing-arrangement.mjs';
import {createDrawingGroup,ungroupDrawing} from './drawing-groups.mjs';
import {DrawingGroupDialog} from './DrawingGroupDialog.jsx';
import {nativeLayoutChanges} from './drawing-containment.mjs';
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

export function DrawioCanvas({graphRef,scene,selected,onSelect,onSelectMany,groups=[],onGroupsChange,onEditRecord,onDoubleClick,onMove,onConnect,onRemove,onContext,
  onDropShape,onRename,onLayout,properties,propertiesVisible,scopeId,onOpenInside,label,scopeLabel,layoutKey,autoFit=true}){
  const container=useRef(null),native=useRef(null),live=useRef(null);
  const [ready,setReady]=useState(false),[failure,setFailure]=useState(''),[referencesOpen,setReferencesOpen]=useState(false),[zoomPercent,setZoomPercent]=useState(100),[panMode,setPanMode]=useState(false),[layoutIssues,setLayoutIssues]=useState([]),[focusedId,setFocusedId]=useState('');
  usePendingWork('Loading drawing…',!ready&&!failure);
  const [arranging,setArranging]=useState(false),[arrangementNote,setArrangementNote]=useState('');
  const arrangingRef=useRef(false);
  usePendingWork('Arranging page…',arranging);
  const [groupMenu,setGroupMenu]=useState(null),[groupAction,setGroupAction]=useState(null);
  live.current={scene,onSelect,onSelectMany,groups,onGroupsChange,onDoubleClick,onMove,onConnect,onRemove,onContext,onRename,onLayout,scopeId,onOpenInside,panMode,label,selected,arrangePage};
  const chosen=scene.vertices.find(v=>v.id===(Array.isArray(selected)?selected[0]:selected)&&v.selectable!==false);

  useEffect(()=>{
    let disposed=false,graph,disposeContext;
    drawioRuntime().then(async mx=>{
      if(disposed)return;
      await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));
      if(disposed)return;
      const element=container.current;
      graph=new mx.mxGraph(element);
      // AtMem owns grouping in the project model. Each native cell moves independently.
      graph.getCompositeParent=cell=>cell;
      graph.getReferenceTerminal=cell=>cell;
      const model=graph.getModel();
      model.maintainEdgeParent=false;
      graph.setDropEnabled(true);
      graph.isValidDropTarget=(cell,moving)=>model.isVertex(cell)&&record(cell)?.selectable!==false&&!moving?.some(item=>item===cell||model.isAncestor(item,cell));
      graph.setExtendParents(false);
      graph.isConstrainChild=()=>false;
      const allCells=()=>live.current.scene.vertices.concat(live.current.scene.wires).map(row=>model.getCell(row.id)).filter(Boolean);
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
      graph.graphHandler.isPropagateSelectionCell=()=>false;
      graph.graphHandler.isDelayedSelection=cell=>graph.isCellSelected(cell)&&graph.getSelectionCount()>1;
      graph.panningHandler.usePopupTrigger=false;
      graph.panningHandler.pinchEnabled=false;
      handle.connectImage=new mx.mxImage(connectionIcon,18,18);
      handle.getIconPosition=(icon,state)=>new mx.mxPoint(
        state.x+state.width-icon.bounds.width-6,state.getCenterY()-icon.bounds.height/2);
      graph.isCellMovable=cell=>Boolean((live.current.onLayout||live.current.onMove)&&model.isVertex(cell)&&(live.current.onLayout||record(cell)?.movable!==false)&&record(cell)?.selectable!==false);
      graph.isCellResizable=cell=>Boolean(live.current.onLayout&&model.isVertex(cell)&&record(cell)?.selectable!==false);
      graph.isCellRotatable=cell=>graph.isCellResizable(cell)&&!record(cell)?.container;
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
        if(performance.now()<suppressClickUntil){event.consume();return;}
        // React owns selection. Native default click handling runs AFTER this listener
        // and would otherwise clear a selection when a label/handle reports no cell.
        if(live.current.onSelect)event.consume();
        const pointer=event.getProperty('event');
        const marker=pointer?.target?.closest?.('[data-record-id]')?.getAttribute('data-record-id');
        const cell=getCell(event)||(marker&&allCells().find(cell=>{
          const row=record(cell);return row&&(row.id===marker||row.recordId===marker);
        }));
        const item=record(cell);
        // The pan handler owns explicit blank clicks. Native redraw/handle clicks
        // can report no cell; they must not erase the controlled selection.
        if(!item||item.selectable===false){
          if(!item&&(pointer?.pointerType==='touch'||pointer?.type?.startsWith('touch')))live.current.onSelect?.(null);
          else api.select(live.current.selected);
          return;
        }
        if(model.isEdge(cell))setReferencesOpen(true);
        live.current.onSelect?.(item.recordId||item.id,pointer);
      });
      graph.addListener(mx.mxEvent.DOUBLE_CLICK,(_sender,event)=>{
        const item=record(getCell(event));
        if(item&&model.isVertex(getCell(event))&&live.current.onOpenInside){event.consume();live.current.onOpenInside(item.id);return;}
        if(item?.visualGroup&&live.current.onGroupsChange){event.consume();setGroupAction({id:item.id,name:item.name});return;}
        if(item&&live.current.onDoubleClick){
          event.consume();
          live.current.onDoubleClick(item.recordId||item.id);
        }
      });
      function persistLayout(changes,options){
        try{live.current.onLayout(changes,options);setFailure('');}catch(error){setFailure(error.message);}
        requestAnimationFrame(()=>{if(!disposed){signature=undefined;api.setScene(live.current.scene);api.select(live.current.selected);}});
      }
      graph.addListener(mx.mxEvent.MOVE_CELLS,(_sender,event)=>{
        if(updating)return;
        suppressClickUntil=performance.now()+150;
        const movable=event.getProperty('cells').filter(cell=>model.isVertex(cell)&&graph.isCellMovable(cell));
        const positions=live.current.onLayout?nativeLayoutChanges(model,allCells().filter(c=>model.isVertex(c))):movable.map(cell=>movedDrawingCell(record(cell),model.getGeometry(cell),{absolute:false}));
        const parents={};for(const cell of movable){const row=record(cell),p=model.getParent(cell),parent=model.isVertex(p)?record(p)?.id:live.current.scopeId||null;if(parent!==(row.containerParentId||null))parents[row.id]=parent;}
        if(movable.length===1)live.current.onSelect?.(record(movable[0]).id);else if(movable.length>1)live.current.onSelectMany?.(movable.map(c=>record(c).id));
        if(movable.length){if(live.current.onLayout)persistLayout(positions,{parents});else live.current.onMove?.(positions);}
      });
      graph.addListener(mx.mxEvent.CELLS_RESIZED,(_sender,event)=>{
        if(updating||!live.current.onLayout)return;
        suppressClickUntil=performance.now()+150;
        persistLayout(nativeLayoutChanges(model,event.getProperty('cells').filter(cell=>graph.isCellResizable(cell))));
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
      const reflectSelection=()=>{
        const cells=graph.getSelectionCells();
        element.dataset.selectedRecords=JSON.stringify(selectionId());
        for(const cell of allCells()){
          const shape=graph.view.getState(cell)?.shape?.node;
          if(shape?.getAttribute('role')==='button')shape.setAttribute('aria-pressed',String(cells.includes(cell)));
        }
        for(const cell of cells){const handler=graph.selectionCellsHandler.getHandler(cell);for(const [i,sizer]of (handler?.sizers||[]).entries())sizer.node?.setAttribute('data-transform-handle',sizer===handler.rotationShape?'rotate':'resize-'+i);}
      };
      graph.getSelectionModel().addListener(mx.mxEvent.CHANGE,()=>{if(!updating)reflectSelection();});
      const keys=event=>{
        if(/INPUT|TEXTAREA/.test(event.target.tagName))return;
        if(event.key==='Escape'){event.stopPropagation();graph.clearSelection();live.current.onSelect?.(null);return;}
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
        const nativeIds=selectionId();
        const current=Array.isArray(live.current.selected)?live.current.selected:nativeIds.length>1?nativeIds:live.current.selected?[live.current.selected]:[];
        const eligible=current.filter(id=>model.isVertex(model.getCell(id)));
        const ids=item&&!eligible.includes(item.id)?[item.id]:eligible;
        if(live.current.onGroupsChange&&(ids.length>1||item?.visualGroup)){
          setGroupMenu({x:Math.min(event.clientX,innerWidth-220),y:Math.min(event.clientY,innerHeight-160),ids,group:item?.visualGroup?item.id:null});return;
        }
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
        arrange(){return live.current.arrangePage();},
        inspect(){return inspectDiagramReadability(graph,graph.atmemRenderedScene||live.current.scene);},
        select(ids){
          const wanted=Array.isArray(ids)?ids:ids?[ids]:[];
          const cells=allCells().filter(cell=>{
            const row=record(cell);
            return row&&wanted.includes(row.recordId||row.id)&&row.selectable!==false;
          });
          const current=graph.getSelectionCells();
          if(current.length!==cells.length||current.some((cell,i)=>cell!==cells[i]))graph.setSelectionCells(cells);
          reflectSelection();
        },
      };
      const updateZoom=()=>{setZoomPercent(Math.round(graph.view.scale*100));reflectSelection();};
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
      const removePan=installCanvasPan(element,graph,{onSelectMany:ids=>live.current.onSelectMany?.(ids),isPanMode:()=>live.current.panMode,onBlankClick:()=>live.current.onSelect?.(null)});
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
  useEffect(()=>{if(!groupMenu)return;const close=e=>{if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();setGroupMenu(null);}};window.addEventListener('keydown',close,true);return()=>window.removeEventListener('keydown',close,true);},[groupMenu]);
  useEffect(()=>{if(container.current)container.current.dataset.pan=panMode?'grab':'';},[panMode]);
  useEffect(()=>{if(propertiesVisible)setReferencesOpen(true);},[propertiesVisible]);
  useEffect(()=>{if(selected&&properties)setReferencesOpen(true);},[selected,Boolean(properties)]);
  useEffect(()=>{if(ready)native.current?.setScene(scene);},[ready,scene]);
  useEffect(()=>{if(ready)native.current?.select(selected);},[ready,scene,selected]);

  async function arrangePage(){
    if(arrangingRef.current||!native.current||!onLayout)return;
    const basis=scene,api=native.current,initial=api.inspect();
    arrangingRef.current=true;setArranging(true);setArrangementNote('');setFailure('');
    let best=null,bestScore=layoutConflictScore(initial.issues),bestCount=initial.issues.length;
    const frame=()=>new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));
    try{
      await frame();
      for(const [spacing,direction] of [[1,'LR'],[1.7,'LR'],[2.6,'LR'],[1,'TB'],[1.7,'TB'],[2.6,'TB']]){
        if(direction==='TB'&&bestCount<=25)continue;
        if(live.current.scene!==basis||native.current!==api)throw Error('The drawing changed. Arrange it again.');
        const candidate=arrangeDrawingScene(basis,{spacing,direction});
        try{updateDrawingLayout(null,'candidate',arrangementChanges(candidate));}catch{continue;}
        api.setScene(candidate);api.fit();
        const check=api.inspect(),score=layoutConflictScore(check.issues);
        if(!check.deferred&&score<bestScore&&check.issues.length<bestCount){best=candidate;bestScore=score;bestCount=check.issues.length;}
        await frame();
        if(bestCount===0)break;
      }
      if(live.current.scene!==basis||native.current!==api)throw Error('The drawing changed. Arrange it again.');
      api.setScene(basis);
      if(best){onLayout(arrangementChanges(best));setArrangementNote('Layout rearranged.');requestAnimationFrame(()=>native.current?.fit());}
      else setArrangementNote('No better arrangement found. Use a focused view.');
    }catch(error){if(native.current===api)api.setScene(live.current.scene);setFailure(error.message);}
    finally{arrangingRef.current=false;setArranging(false);}
  }
  function focusIssue(issue){
    const ids=[issue.id,issue.other].filter(Boolean),nodes=new Set();
    for(const id of ids){const edge=scene.wires.find(w=>w.id===id);if(edge){nodes.add(edge.source);nodes.add(edge.target);}else nodes.add(id);}
    native.current?.select(ids);onSelect?.(issue.id);requestAnimationFrame(()=>native.current?.fit({nodes:[...nodes].map(id=>({id})),minZoom:.2,maxZoom:1}));
  }
  function saveGroup(name){
    let next,id;
    if(groupAction.id){id=groupAction.id;next=groups.map(g=>g.id===id?{...g,name:name.trim()}:g);}
    else{const created=createDrawingGroup(groups,scene,groupAction.ids,name);next=created.groups;id=created.id;}
    const memberIds=next.find(g=>g.id===id)?.memberIds||[],owners=[...new Set(memberIds.map(member=>scene.vertices.find(v=>v.id===member)?.containerParentId||scopeId||null))];
    onGroupsChange(next,groupAction.id?undefined:{parents:{[id]:owners.length===1?owners[0]:scopeId||null}});setGroupAction(null);setGroupMenu(null);onSelectMany?.([]);onSelect?.(id);
  }
  return <div className="drawio-surface" data-properties-open={referencesOpen}>
    {groupMenu&&<><button className="drawing-group-dismiss" aria-label="Close group menu" onClick={()=>setGroupMenu(null)}/><div role="menu" aria-label="Grouping" className="drawing-group-menu" style={{left:groupMenu.x,top:groupMenu.y}}>
      {groupMenu.ids.length>1&&<button role="menuitem" onClick={()=>{setGroupAction({ids:groupMenu.ids});setGroupMenu(null);}}>Group selection</button>}
      {groupMenu.group&&<><button role="menuitem" onClick={()=>{setGroupAction({id:groupMenu.group,name:groups.find(g=>g.id===groupMenu.group)?.name});setGroupMenu(null);}}>Rename group</button><button role="menuitem" onClick={()=>{onGroupsChange(ungroupDrawing(groups,groupMenu.group));onSelect?.(null);setGroupMenu(null);}}>Ungroup</button></>}
    </div></>}
    {groupAction&&<DrawingGroupDialog initial={groupAction.name} onClose={()=>setGroupAction(null)} onSave={saveGroup}/>}


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
    {!!layoutIssues.length&&<div className="diagram-layout-issues" role="status" aria-busy={arranging}>{layoutIssues.length} layout conflicts.{arrangementNote&&<span className="diagram-arrangement-note">{arrangementNote}</span>}<details><summary>Review affected elements</summary><ul>{layoutIssues.map((issue,i)=><li key={i} data-layout-issue={issue.kind} data-issue-id={issue.id} data-issue-other={issue.other}><button type="button" onClick={()=>focusIssue(issue)}>{issue.kind.replaceAll('-',' ')} · {[...scene.vertices,...scene.wires].find(r=>r.id===issue.id)?.name||issue.id}</button></li>)}</ul></details>{onLayout&&!scene.timeline&&!scene.ordered&&<button type="button" disabled={arranging} aria-busy={arranging} onClick={arrangePage}>{arranging?'Arranging…':'Arrange page'}</button>}</div>}
    {arrangementNote&&!layoutIssues.length&&<div className="diagram-arrangement-note" role="status">{arrangementNote}</div>}
    {!!scene.vertices.length&&<div className="diagram-navigation">
      {onGroupsChange&&Array.isArray(selected)&&selected.length>1&&<button type="button" onClick={()=>setGroupAction({ids:selected})}>Group selection</button>}
      {onOpenInside&&chosen&&<button type="button" onClick={()=>onOpenInside(chosen.id)}>Open inside</button>}
      <button type="button" aria-label="Pan drawing" aria-pressed={panMode} onClick={()=>setPanMode(v=>!v)}>Pan</button>
      <label>Focus <select aria-label="Focus diagram element" value={focusedId} onChange={event=>{
        const id=event.target.value;if(!id)return;onSelect?.(id);requestAnimationFrame(()=>native.current?.fit({nodes:[{id}],minZoom:scene.vertices.find(v=>v.id===id)?.container?.1:1,maxZoom:1}));
      }}><option value="">Find an element…</option>{scene.vertices.filter(v=>v.selectable!==false).map(v=><option key={v.id} value={v.id}>{v.name}</option>)}</select></label>
      {onLayout&&chosen&&<details className="diagram-transform"><summary>Size &amp; rotation</summary><form key={chosen.id+':'+chosen.width+':'+chosen.height+':'+chosen.rotation} onSubmit={event=>{
        event.preventDefault();const data=new FormData(event.currentTarget);try{onLayout([{id:chosen.id,width:Number(data.get('width')),height:Number(data.get('height')),rotation:chosen.container?0:Number(data.get('rotation'))}]);setFailure('');}catch(error){setFailure(error.message);}
      }}><label>Width<input aria-label="Element width" name="width" type="number" min="40" max="10000" defaultValue={Math.round(chosen.width)} required/></label><label>Height<input aria-label="Element height" name="height" type="number" min="40" max="10000" defaultValue={Math.round(chosen.height)} required/></label><label>Rotation<input aria-label="Element rotation" disabled={chosen.container} name="rotation" type="number" min="0" max="359" defaultValue={chosen.rotation||0} required/></label><button type="submit">Apply transform</button><button type="button" title="Remove manual positions, sizes and rotations" onClick={()=>onLayout(null)}>Restore original layout</button></form></details>}
      <button type="button" aria-label="Zoom out drawing" onClick={()=>native.current?.zoom(-.15)}>−</button><button type="button" aria-label="Fit drawing" onClick={()=>native.current?.fit()}>Fit</button><button type="button" aria-label="Zoom in drawing" onClick={()=>native.current?.zoom(.15)}>+</button>
      <button type="button" onClick={()=>native.current?.fit({minZoom:1,maxZoom:1})} aria-label="Read diagram at actual size">{zoomPercent<75?'Read labels · ':''}{zoomPercent}%</button>
    </div>}
    {(!!scene.vertices.length||onOpenInside||properties)&&<DiagramReferences propertiesVisible={propertiesVisible} properties={chosen?.visualGroup&&onGroupsChange&&<div className="drawing-group-actions"><strong>{chosen.name}</strong><button className="btn" onClick={()=>setGroupAction({id:chosen.id,name:chosen.name})}>Rename group</button><button className="btn" onClick={()=>{onGroupsChange(ungroupDrawing(groups,chosen.id));onSelect?.(null);}}>Ungroup</button></div>||properties} scene={scene} selected={selected} onEdit={onEditRecord} onSelect={id=>{native.current?.select(id);onSelect?.(id);}} open={referencesOpen} onToggle={()=>setReferencesOpen(value=>!value)}/>}
    {failure&&<p role="alert" className="drawio-load-error">{failure}</p>}
  </div>;
}
