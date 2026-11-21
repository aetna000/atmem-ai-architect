import {readBoundedEvidence} from './evidence-download.mjs';
import {handoffDigest,blockHandoffExportFiles} from './block-handoff.mjs';
const SHA=/^[a-f0-9]{64}$/;
const MAX_IMAGE=3*1024*1024,MAX_TOTAL=64*1024*1024,MAX_COUNT=256;
// Retained normalized pixels are evidence, never reconstructed diagrams or inferred OCR.
export async function attachSourceFigureFiles(project,originalFiles,{session,fetcher=fetch}={}){
 const sources=project.extensions?.designSources||[];
 const figures=sources.flatMap(source=>(source.figureEvidence?.figures||[]).map(figure=>({source,figure})));
 if(figures.length>MAX_COUNT)throw Error('Source evidence exceeds 256 figures; no export content was discarded.');
 const files={...originalFiles},receipts=[];let total=0;
 if(!figures.length)return {files,evidence:{embedded:0,referenced:0,complete:true}};
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),60000);
 try{for(const {source,figure}of figures){
  const row={...figure,sourceSha256:source.sha256,manifestSha256:source.figureEvidence.manifestSha256,embedded:false};
  receipts.push(row);
  if(figure.status!=='available'){row.exportStatus='source_unavailable';continue;}
  if(!session?.token){row.exportStatus='session_unavailable';continue;}
  if(!SHA.test(source.sha256)||!SHA.test(row.manifestSha256)||!SHA.test(figure.sha256)||!/^figure-[1-9][0-9]*$/.test(figure.id))throw Error('Source figure provenance is invalid; export stopped.');
  let response;
  try{response=await fetcher('/api/design-sources/figure',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.token}`},body:JSON.stringify({projectId:project.id,sourceSha256:source.sha256,manifestSha256:row.manifestSha256,figureId:figure.id}),signal:controller.signal});}
  catch{row.exportStatus=controller.signal.aborted?'retrieval_timeout':'service_unavailable';continue;}
  if(!response.ok){row.exportStatus='retrieval_failed';row.httpStatus=response.status;continue;}
  if(response.headers.get('content-type')?.split(';')[0]!=='image/png'||response.headers.get('X-Source-Sha256')!==source.sha256||response.headers.get('X-Manifest-Sha256')!==row.manifestSha256||response.headers.get('X-Figure-Sha256')!==figure.sha256)throw Error('Source figure response does not match the requested provenance.');
  const bytes=await readBoundedEvidence(response,MAX_IMAGE,'Source figure');
  if(handoffDigest(bytes)!==figure.sha256||bytes.length!==figure.bytes)throw Error('Source figure integrity check failed; export stopped.');
  total+=bytes.length;if(total>MAX_TOTAL)throw Error('Source figures exceed 64 MB; export stopped without discarding content.');
  row.path=`sources/${source.sha256}/figures/${figure.id}.png`;row.embedded=true;row.exportStatus='verified';files[row.path]=bytes;
 }}finally{clearTimeout(timer);}
 const evidence={embedded:receipts.filter(row=>row.embedded).length,referenced:receipts.length,complete:receipts.every(row=>row.embedded),boundary:'Normalized image byte custody only; not original document bytes, OCR or architecture interpretation.'};
 files['source-figures.json']=JSON.stringify({...evidence,figures:receipts},null,2)+'\n';
 if(files['handoff-readiness.json']){const readiness=JSON.parse(files['handoff-readiness.json']);readiness.sourceFigures=receipts;readiness.sourceEvidence=evidence;files['handoff-readiness.json']=JSON.stringify(readiness,null,2)+'\n';}
 files['sources/README.md']='# Source image evidence\n\n'+receipts.map(row=>`- ${row.sourceSha256} / ${row.id}: ${row.exportStatus}${row.path?' · '+row.path:''}`).join('\n')+'\n\nUnavailable images require the original source in this project. Inspect handoff-readiness.json for provenance and location metadata.\n';
 const note='\n## Source images\n\nSee sources/README.md and source-figures.json. Verified retained images are included under sources/. Unavailable evidence remains explicitly referenced; no image interpretation is inferred.\n';
 if(files['READ_ME_FIRST.md']){files['READ_ME_FIRST.md']+=note;files['START_HERE.md']=files['READ_ME_FIRST.md'];}else if(files['START_HERE.md'])files['START_HERE.md']+=note;
 return {files,evidence};
}

export async function attachHandoffSourceFigures(handoff,options){
 const source=JSON.parse(handoff.files['source-context.json']);
 const {files}=await attachSourceFigureFiles({id:handoff.projectId,extensions:source.extensions},handoff.files,options);
 const result={...handoff,files};return {handoff:result,files:blockHandoffExportFiles(result)};
}
