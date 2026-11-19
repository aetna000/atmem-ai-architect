import {handoffDigest,blockHandoffExportFiles} from './block-handoff.mjs';
const SHA=/^[a-f0-9]{64}$/;
const EXPORT_RECEIPTS=new Set(['manifest.json','handoff-manifest.json','captured-evidence.json','design-evidence.json','design-documents-receipt.json','source-figures.json','handoff-readiness.json','evidence/initial-context-receipt.json','evidence/original-native-capture.zip','evidence/original-agent-handoff.zip']);
const decode=value=>typeof value==='string'?value:new TextDecoder('utf-8',{fatal:true}).decode(value);
const length=value=>typeof value==='string'?new TextEncoder().encode(value).length:value.byteLength;
const safe=name=>typeof name==='string'&&name.length<=500&&!/[\\:\x00-\x1f\x7f]/.test(name)&&name.split('/').every(part=>part&&part!=='.'&&part!=='..');
function json(files,name){if(!Object.hasOwn(files,name))throw Error('Missing evidence file '+name);return JSON.parse(decode(files[name]));}
function matches(bytes,receipt,label){if(!receipt||!SHA.test(receipt.sha256)||handoffDigest(bytes)!==receipt.sha256||length(bytes)!==receipt.bytes)throw Error(label+' integrity check failed.');}

// Pure, bounded assembly from operator-supplied immutable captures and receipts.
// Custody is checked here; a hosted API must authenticate project scope separately.
export function supplementCapturedHandoff({handoffFiles,handoffArchive,captureFiles,captureArchive,captureManifest,submittedContext,initialContext,initialReceipt}){
 if(Object.keys(handoffFiles).length>2000||!Array.isArray(captureManifest.files)||captureManifest.files.length>2000||length(handoffArchive)>64_000_000||length(captureArchive)>64_000_000||length(submittedContext)>2_000_000||length(initialContext)>2_000_000)throw Error('Captured evidence exceeds its input bound.');
 const original=json(handoffFiles,'handoff-manifest.json');
 if(original.format!=='atmem.external-agent-handoff'||original.version!==1||!original.files||!Array.isArray(original.blockIds))throw Error('Unsupported original handoff.');
 const source=json(handoffFiles,'source-context.json'),documents=source.extensions?.architectureDocuments;
 if(source.meta?.id!==original.projectId||handoffDigest(handoffFiles['source-context.json'])!==original.sourceSha256)throw Error('Handoff source identity mismatch.');
 for(const [name,receipt]of Object.entries(original.files)){if(!safe(name)||!Object.hasOwn(handoffFiles,name))throw Error('Original handoff has a missing or unsafe path.');matches(handoffFiles[name],receipt,'Original handoff '+name);}
 if(Object.keys(handoffFiles).some(name=>name!=='handoff-manifest.json'&&!Object.hasOwn(original.files,name)))throw Error('Original handoff has unlisted files.');
 const prepared=mergeCapturedEvidence({projectId:original.projectId,documents,originalFiles:Object.fromEntries(Object.entries(handoffFiles).filter(([name])=>name!=='handoff-manifest.json')),handoffArchive,captureFiles,captureArchive,captureManifest,submittedContext,initialContext,initialReceipt});
 return blockHandoffExportFiles({...original,files:prepared.files});
}

// Shared merge for root and scoped exports. Authenticated retrieval is separate.
export function mergeCapturedEvidence({projectId,documents,originalFiles,sourceFile='source-context.json',handoffArchive,captureFiles,captureArchive,captureManifest,submittedContext,initialContext,initialReceipt}){
 if(Object.keys(originalFiles).length>2000||!Array.isArray(captureManifest.files)||captureManifest.files.length>2000||length(captureArchive)>64_000_000||length(submittedContext)>2_000_000||length(initialContext)>2_000_000)throw Error('Captured evidence exceeds its input bound.');
 if(captureManifest.id!==documents?.artifactId||!SHA.test(captureManifest.sha256)||handoffDigest(captureArchive)!==captureManifest.sha256||length(captureArchive)!==captureManifest.bytes||captureManifest.turnStatus!=='completed'||captureManifest.kind!=='delivery')throw Error('Captured artifact does not match the reviewed source.');
 if(handoffDigest(submittedContext)!==documents.contextSha256||JSON.parse(decode(submittedContext)).meta?.id!==projectId)throw Error('Submitted context identity mismatch.');
 if(handoffDigest(captureFiles['architecture.canvas.json'])!==documents.draftSha256||!decode(captureFiles['architecture.review.md']).replaceAll('\r\n','\n').split('\n').includes('Draft SHA-256: '+documents.draftSha256))throw Error('Captured draft/review seal mismatch.');
 for(const document of documents.files||[])if(!Object.hasOwn(captureFiles,document.path)||handoffDigest(captureFiles[document.path])!==document.sha256)throw Error('Captured authored document differs from the pinned design.');
 const records=(captureManifest.files||[]).filter(row=>row.kind==='file'),known=new Set(),captured=[];
 for(const row of records){if(!safe(row.path)||known.has(row.path.toLowerCase())||!Object.hasOwn(captureFiles,row.path))throw Error('Captured file inventory is unsafe, missing or ambiguous.');known.add(row.path.toLowerCase());matches(captureFiles[row.path],row,'Captured '+row.path);captured.push(row);}
 if(Object.keys(captureFiles).some(name=>!name.endsWith('/')&&!records.some(row=>row.path===name)))throw Error('Captured archive has unlisted files.');
 let historical;try{historical=JSON.parse(decode(initialContext));}catch{/* Legacy initial inputs can be opaque bytes; the creation receipt binds scope. */}
 if(initialReceipt.projectId!==projectId||initialReceipt.sessionId!==captureManifest.sessionId||(historical?.meta?.id!==undefined&&historical.meta.id!==projectId))throw Error('Historical input scope mismatch.');
 matches(initialContext,initialReceipt,'Historical initial context');
 const files={...originalFiles};const added=[],archiveOnly=[];
 function add(name,value,origin){if(!safe(name)||['AGENTS.md','SKILL.md'].includes(name)||name.startsWith('.agents/')||name.startsWith('.codex/'))throw Error('Captured content cannot replace repository controls.');const key=name.toLowerCase();if(Object.keys(files).some(existing=>existing!==name&&(existing.toLowerCase()===key||existing.toLowerCase().startsWith(key+'/')||key.startsWith(existing.toLowerCase()+'/'))))throw Error('Captured content has a case or file/directory conflict with '+name);if(Object.hasOwn(files,name)){if(handoffDigest(files[name])!==handoffDigest(value))throw Error('Captured content conflicts with '+name);return;}files[name]=value;added.push({path:name,sha256:handoffDigest(value),bytes:length(value),origin});}
 for(const row of captured){
  const parts=row.path.toLowerCase().split('/');
  if(EXPORT_RECEIPTS.has(row.path.toLowerCase())||parts.some(part=>['agents.md','skill.md','.agents','.codex','.git'].includes(part))||row.path.toLowerCase().startsWith('.github/workflows/'))archiveOnly.push({...row,reason:'Retained in the original capture only; never replace receiving repository controls.'});
  else if(row.path==='README.md'&&Object.hasOwn(files,'README.md')&&handoffDigest(files['README.md'])!==row.sha256&&Object.hasOwn(files,'NATIVE_DESIGN.md')&&handoffDigest(files['NATIVE_DESIGN.md'])===row.sha256)archiveOnly.push({...row,exportPath:'NATIVE_DESIGN.md',reason:'Exact authored README is retained as NATIVE_DESIGN.md; keep generated receiving README.'});
  else add(row.path,captureFiles[row.path],'immutable_native_capture');
 }
 add('project-context.json',initialContext,'historical_initial_context');
 if(handoffArchive)add('evidence/original-agent-handoff.zip',handoffArchive,'original_handoff');
 add('evidence/original-native-capture.zip',captureArchive,'original_capture');
 add('evidence/initial-context-receipt.json',JSON.stringify(initialReceipt,null,2)+'\n','initial_input_receipt');
 files['captured-evidence.json']=JSON.stringify({version:1,artifactId:captureManifest.id,artifactSha256:captureManifest.sha256,...(handoffArchive?{originalHandoffSha256:handoffDigest(handoffArchive)}:{}),submittedContextSha256:documents.contextSha256,draftSha256:documents.draftSha256,initialContextSha256:initialReceipt.sha256,files:added,archiveOnly,boundary:'Exact captured code, documents and recorded evidence. Historical inputs are not current requirements; assembly does not build, test, deploy or authenticate external tenants.'},null,2)+'\n';
 const note=`\n## Captured source and evidence\n\nThe current design is ${sourceFile}. project-context.json is the exact historical initial input, not the current design. captured-evidence.json records the attached native code and evidence. The original capture ZIP is preserved under evidence/. The archive remains complete project evidence; module assignment stays in handoff-manifest.json when present. Retained implementation and recorded checks do not establish acceptance of the complete current design. Read the destination repository instructions before changing or executing code.\n`;
 if(files['READ_ME_FIRST.md']){files['READ_ME_FIRST.md']+=note;files['START_HERE.md']=files['READ_ME_FIRST.md'];}else if(files['START_HERE.md'])files['START_HERE.md']+=note;
 const total=Object.values(files).reduce((sum,value)=>sum+length(value),0);if(Object.keys(files).length>2000||total>64_000_000)throw Error('Supplemented handoff exceeds its evidence bound; no content was discarded.');
 return {files,receipt:JSON.parse(files['captured-evidence.json'])};
}
