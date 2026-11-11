// Shared context/dependency model. Currency means exact context agreement, never
// proof that a claimed implementation, test, account plan or deployment succeeded.
import {engineeringConversation} from './engineering-client.mjs';
export const WORK_VERSION=1;
export const WORK_KINDS=['responsibility','delivery-unit','interface','implementation','assumption','decision','evidence','requirement'];
const clone=value=>JSON.parse(JSON.stringify(value));
const order=(a,b)=>a<b?-1:a>b?1:0;
const plain=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
export function canonicalWork(value){
 return JSON.stringify(value,(_,v)=>plain(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
}
function text(value,max,name){if(typeof value!=='string'||!value.trim()||[...value].length>max)throw Error(`Invalid ${name}; no content was truncated.`);return value;}
function only(value,keys,name){if(!plain(value)||Object.keys(value).some(k=>!keys.includes(k)))throw Error(`Invalid ${name} shape; retain the original file.`);}
function ref(value){return text(value,240,'work reference');}
function array(value,max,name){if(!Array.isArray(value)||value.length>max)throw Error(`Invalid or oversized ${name}; no records were discarded.`);}
function assertWorkJSON(v,depth=0){if(depth>40)throw Error('Architecture work is nested too deeply.');if(v===null||typeof v==='string'||typeof v==='boolean')return;if(typeof v==='number'&&Number.isFinite(v))return;if(Array.isArray(v)){v.forEach(x=>assertWorkJSON(x,depth+1));return;}if(plain(v)&&[Object.prototype,null].includes(Object.getPrototypeOf(v))){Object.values(v).forEach(x=>assertWorkJSON(x,depth+1));return;}throw Error('Work data must be lossless finite JSON values.');}

export function emptyArchitectureWork(){return {version:WORK_VERSION,records:[],intents:[],snapshots:[],bindings:[],history:[]};}
export function validateArchitectureWork(value){
 if(value===undefined)return emptyArchitectureWork();
 only(value,['version','records','intents','snapshots','bindings','history'],'architecture work');
 if(value.version!==WORK_VERSION)throw Error('Unsupported architecture work version; retain the file and use a compatible reader.');
 for(const key of ['records','intents','snapshots','bindings','history'])array(value[key],key==='snapshots'?4000:1000,key);
 const unique=(items,key,name)=>{const seen=new Set();for(const item of items){const id=ref(item[key]);if(seen.has(id))throw Error(`Duplicate ${name}: ${id}`);seen.add(id);}};
 unique(value.records,'id','work record');unique(value.intents,'id','engineering intent');unique(value.snapshots,'id','context snapshot');unique(value.bindings,'ref','context binding');
 for(const r of value.records){
  only(r,['id','kind','title','description','source','agreement','dependsOn','data'],'work record');
  if(!WORK_KINDS.includes(r.kind)||!['user','agent','import'].includes(r.source)||!['proposed','accepted'].includes(r.agreement))throw Error('Record explicit work kind, provenance and agreement.');
  text(r.id,200,'work record ID');text(r.title,200,'work title');if(typeof r.description!=='string'||[...r.description].length>16000||!plain(r.data))throw Error('Invalid work description/data; no content was truncated.');
  array(r.dependsOn,100,'work dependencies');r.dependsOn.forEach(ref);if(new Set(r.dependsOn).size!==r.dependsOn.length)throw Error('Duplicate work dependency.');
  if(r.kind==='implementation'&&r.data.files!==undefined){array(r.data.files,200,'implementation files');for(const file of r.data.files){text(file,500,'implementation path');if(file.startsWith('/')||/^[A-Za-z]:/.test(file)||/[\x00-\x1f]/.test(file)||file.includes('\\')||file.split('/').some(p=>!p||p==='.'||p==='..'))throw Error('Implementation paths must be relative project files.');}}
 }
 for(const i of value.intents){
  only(i,['id','sessionId','sequence','text','status'],'engineering intent');text(i.sessionId,100,'session ID');text(i.text,80000,'engineering intent');
  if(!Number.isSafeInteger(i.sequence)||i.sequence<1||!['accepted','pending','uncertain'].includes(i.status))throw Error('Invalid engineering intent identity/status.');
  if(i.id!==`${i.sessionId}:${i.sequence}`)throw Error('Engineering intent identity differs from its session/sequence.');
 }
 const snapshots=new Map(value.snapshots.map(s=>[s.id,s]));
 for(const s of value.snapshots){only(s,['id','ref','value'],'context snapshot');ref(s.ref);if(!plain(s.value)||s.value.id!==s.ref)throw Error('Invalid context snapshot value.');}
 for(const b of [...value.bindings,...value.history]){
  only(b,['ref','snapshotIds','recordedAt','recordedBy','scope'],'context binding');array(b.snapshotIds,2000,'binding sources');b.snapshotIds.forEach(ref);
  if(new Set(b.snapshotIds).size!==b.snapshotIds.length||!b.snapshotIds.length||b.snapshotIds.some(id=>!snapshots.has(id)))throw Error('A context binding needs unique retained source snapshots.');
  const refs=b.snapshotIds.map(id=>snapshots.get(id).ref);if(new Set(refs).size!==refs.length||!refs.includes(b.ref))throw Error('A binding must retain its own source exactly once.');
  if(b.scope!=='context_review_only'||!['user','agent','import'].includes(b.recordedBy)||!/^\d{4}-\d\d-\d\dT/.test(b.recordedAt)||!Number.isFinite(Date.parse(b.recordedAt)))throw Error('Context review is distinct from executed evidence.');
 }
 assertWorkJSON(value);
 const encoded=JSON.stringify(value);if(new TextEncoder().encode(encoded).length>1_500_000)throw Error('Architecture work history exceeds its storage bound; retain/archive it before adding more. Nothing was discarded.');
 return clone(value);
}
const stateOf=project=>validateArchitectureWork(project.extensions?.architectureWork);
function store(project,state){validateArchitectureWork(state);return {...project,extensions:{...project.extensions,architectureWork:state}};}

export function architectureSources(project,state=stateOf(project)){
 const entries=[];const add=(id,kind,title,value,dependsOn=[])=>entries.push({id,kind,title,value:clone(value),dependsOn:[...new Set([...(id==='project:identity'?[]:['project:identity']),...dependsOn])].sort()});
 add('project:identity','identity','Project identity',{id:project.id||null});
 add('intent:project','intent','Project intent',{text:project.requirements||''});
 add('selection:provider','selection','Selected target provider',{provider:project.provider||'tools'});
 const global=['intent:project','selection:provider',...state.intents.map(i=>'intent:'+i.id)];
 for(const i of state.intents)add('intent:'+i.id,'intent','Engineering request '+i.sequence,i);
 for(const r of project.needs||[])add('requirement:'+r.id,'requirement',r.statement,r);
 for(const a of project.assumptions||[])add('assumption:'+a.id,'assumption',a.statement,a);
 for(const q of project.openQuestions||[])add('question:'+q.id,'question',q.question,q);
 for(const d of project.decisions||[])add('decision:'+d.id,'decision',d.title||d.subject||d.id,d,(d.requirementIds?.length?d.requirementIds:(project.needs||[]).filter(r=>!d.links?.length||r.links?.some(id=>d.links.includes(id))).map(r=>r.id)).map(id=>'requirement:'+id));
 for(const n of project.nodes||[]){
  if(n.data.kind==='note')continue;
  const {inputPosition,outputPosition,...meaning}=n.data;
  const linked=(rows,type)=>rows.filter(r=>r.links?.includes(n.id)).map(r=>type+':'+r.id);
  const decisions=(project.decisions||[]).filter(d=>d.status==='Accepted'&&(!d.links?.length||d.links.includes(n.id))).map(d=>'decision:'+d.id);
  add('block:'+n.id,'responsibility',n.data.label,meaning,[...global,...linked(project.needs||[],'requirement'),...linked(project.assumptions||[],'assumption'),...linked(project.openQuestions||[],'question'),...decisions]);
 }
 for(const e of project.edges||[]){
  const {id,source,target,label,access,integration}=e;
  add('interface:'+id,'interface',label||id,{source,target,...(label!==undefined?{label}:{}),...(access!==undefined?{access}:{}),...(integration!==undefined?{integration}:{})},['block:'+source,'block:'+target]);
 }
 for(const r of state.records)add('work:'+r.id,r.kind,r.title,r,[...global,...r.dependsOn]);
 if(new Set(entries.map(e=>e.id)).size!==entries.length)throw Error('Duplicate architecture source identity.');
 return entries.sort((a,b)=>order(a.id,b.id));
}
function context(entries,target){
 const byId=new Map(entries.map(e=>[e.id,e])),values=new Map(),missing=new Set(),pending=[target];
 while(pending.length){const id=pending.pop();if(values.has(id)||missing.has(id))continue;const entry=byId.get(id);if(!entry){missing.add(id);continue;}values.set(id,entry);pending.push(...entry.dependsOn);}
 return {values,missing:[...missing].sort()};
}
export function architectureWork(project){
 const state=stateOf(project),sources=architectureSources(project,state),snapshots=new Map(state.snapshots.map(s=>[s.id,s]));
 const bindings=new Map(state.bindings.map(b=>[b.ref,b]));
 const currentValues=new Map(sources.map(e=>[e.id,canonicalWork(e)])),previousValues=new Map(state.snapshots.map(s=>[s.id,canonicalWork(s.value)]));
 const entities=sources.map(entry=>{
  const current=context(sources,entry.id),binding=bindings.get(entry.id),previous=new Map((binding?.snapshotIds||[]).map(id=>{const s=snapshots.get(id);return [s.ref,previousValues.get(s.id)];}));
  const changed=binding?[...new Set([...current.values.keys(),...previous.keys()])].filter(id=>currentValues.get(id)!==previous.get(id)).sort():[];
  return {...entry,contextStatus:current.missing.length?'missing':!binding?'unreviewed':changed.length?'changed':'current',changedRefs:changed,missingRefs:current.missing,review:binding?{recordedAt:binding.recordedAt,recordedBy:binding.recordedBy,scope:binding.scope}:null};
 });
 // Preserve deleted targets as visible orphans, including the original snapshots.
 for(const b of state.bindings)if(!entities.some(e=>e.id===b.ref))entities.push({id:b.ref,kind:'removed',title:b.ref,contextStatus:'missing',changedRefs:[],missingRefs:[b.ref],review:{recordedAt:b.recordedAt,recordedBy:b.recordedBy,scope:b.scope}});
 return {format:'atmem.architecture-work',version:WORK_VERSION,projectId:project.id||null,entities,
  boundary:'Context currency and recorded mappings only. Evidence entries are claims/references, not independently verified execution or acceptance. Free-form engineering intent conservatively affects every work mapping until explicitly reconciled.'};
}
export function workContextIdentity(project,target){
 const current=context(architectureSources(project),target);
 return canonicalWork({sources:Object.fromEntries(current.values),missing:current.missing});
}
export function applyArchitectureChange(project,owner,change){
 if(project.id!==owner)return project;
 if(change.kind==='propose')return proposeWorkRecords(project,change.records);
 if(change.kind==='review')return reviewWorkContext(project,change.ref,{expectedContext:change.expectedContext});
 throw Error('Unknown architecture work change.');
}
export function reviewWorkContext(project,target,{recordedBy='user',now=new Date(),expectedContext}={}){
 if(!project.id)throw Error('Save the project identity before recording context review.');
 const state=stateOf(project),current=context(architectureSources(project,state),target);
 if(expectedContext!==undefined&&expectedContext!==canonicalWork({sources:Object.fromEntries(current.values),missing:current.missing}))throw Error('Work context changed; inspect its current sources before reviewing.');
 if(current.missing.length||!current.values.size)throw Error('Resolve missing work references before recording context review.');
 const snapshots=[...state.snapshots],ids=[];
 let next=1;for(const s of snapshots){const n=Number(/^basis-(\d+)$/.exec(s.id)?.[1]);if(Number.isSafeInteger(n))next=Math.max(next,n+1);}
 for(const [id,value] of [...current.values].sort(([a],[b])=>order(a,b))){
  let snapshot=snapshots.find(s=>s.ref===id&&canonicalWork(s.value)===canonicalWork(value));
  if(!snapshot){snapshot={id:'basis-'+next++,ref:id,value};snapshots.push(snapshot);}ids.push(snapshot.id);
 }
 const binding={ref:target,snapshotIds:ids,recordedAt:now.toISOString(),recordedBy,scope:'context_review_only'};
 const previous=state.bindings.find(b=>b.ref===target);
 return store(project,{...state,snapshots,bindings:[...state.bindings.filter(b=>b.ref!==target),binding],history:[...state.history,...(previous?[previous]:[])]});
}
export function proposeWorkRecords(project,records){
 const state=stateOf(project);array(records,200,'work proposal');const byId=new Map(state.records.map(r=>[r.id,r]));
 for(const row of records){
  assertWorkJSON(row);
  if(byId.has(row.id))throw Error('A work proposal cannot overwrite an existing mapping; revise it explicitly.');
  byId.set(row.id,{...clone(row),source:'agent',agreement:'proposed'});
 }
 return store(project,{...state,records:[...byId.values()]});
}
export function synchronizeEngineeringIntent(project,sessionId,events,owner=project.id){
 if(project.id!==owner)return project;
 text(sessionId,100,'session ID');const state=stateOf(project),byId=new Map(state.intents.map(i=>[i.id,i]));let changed=false;
 const rank={pending:0,uncertain:1,accepted:2};
 for(const entry of engineeringConversation(events).filter(e=>e.role==='user')){
  const id=`${sessionId}:${entry.id}`,old=byId.get(id);
  if(old&&old.text!==entry.text)throw Error('Saved engineering intent changed identity; retain both histories for reconciliation.');
  const status=old&&rank[old.status]>rank[entry.status]?old.status:entry.status;
  const value={id,sessionId,sequence:entry.id,text:entry.text,status};
  if(canonicalWork(old)!==canonicalWork(value)){byId.set(id,value);changed=true;}
 }
 const sessions=new Map([...new Set([...state.intents.map(i=>i.sessionId),sessionId])].map((id,index)=>[id,index]));
 return changed?store(project,{...state,intents:[...byId.values()].sort((a,b)=>sessions.get(a.sessionId)-sessions.get(b.sessionId)||a.sequence-b.sequence)}):project;
}
