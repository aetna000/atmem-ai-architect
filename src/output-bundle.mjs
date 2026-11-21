import {verifiedReceipt} from './validation-receipt.mjs';
import {deliveryPack} from './delivery.mjs';
export const VISUAL_PATHS=['spec-kit/implementation-spec.pdf','specification.pdf','diagram.svg','diagram.png','diagram.pdf'];
export async function outputBundle(project,run,environment,checks,{deferVisuals=false,session,prepareSources}={}){
  const snapshot=structuredClone(project);
  const files=deliveryPack(snapshot,run,environment);
  if(checks){const terraform=Object.fromEntries(Object.entries(files).filter(([name])=>name.startsWith('terraform/')).map(([name,value])=>[name.slice(10),value]));const receipt=await verifiedReceipt(terraform,checks);if(receipt)files['terraform/validation-receipt.json']=JSON.stringify(receipt,null,2);}
  const manifest=JSON.parse(files['manifest.json']);manifest.files=Object.keys(files);
  files['manifest.json']=JSON.stringify(manifest,null,2);
  const slug=snapshot.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'atflow';
  const base={project,files,manifest,filename:`${slug}-r${snapshot.revision}-delivery.zip`,visualPaths:VISUAL_PATHS};
  let pending;
  async function prepare(){
    if(!pending)pending=(async()=>{
      const sourceSession=(snapshot.extensions?.architectureDocuments||snapshot.extensions?.designSources?.some(source=>source.figureEvidence?.figures?.length))&&prepareSources?await prepareSources(project):session;
      const {attachReviewedDraftFiles}=await import('./reviewed-draft.mjs');
      const evidence=await attachReviewedDraftFiles(snapshot,files,{session:sourceSession});
      const {attachCapturedEvidenceFiles}=await import('./capture-download.mjs');
      const captured=await attachCapturedEvidenceFiles(snapshot,evidence.files,{session:sourceSession,sourceFile:'project.atmem-ai-architect.json'});
      const {attachSourceFigureFiles}=await import('./source-handoff.mjs');
      const figures=await attachSourceFigureFiles(snapshot,captured.files,{session:sourceSession});
      const {visualFiles}=await import('./visual-export.mjs');
      const fullFiles={...figures.files,...await visualFiles(snapshot,files['specification.md'],files['spec-kit/implementation-spec.md'])};
      const fileDigests=Object.fromEntries(await Promise.all(Object.entries(fullFiles).filter(([name])=>name!=='manifest.json').map(async([name,content])=>{
        const bytes=typeof content==='string'?new TextEncoder().encode(content):content;
        const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(byte=>byte.toString(16).padStart(2,'0')).join('');
        return [name,{sha256:digest,bytes:bytes.byteLength}];
      })));
      const fullManifest={...manifest,files:Object.keys(fullFiles),fileDigests,hashBoundary:'Payload files only; manifest is excluded from its own hashes.',implementationExecutedByExport:false,deploymentExecutedByExport:false};
      fullFiles['manifest.json']=JSON.stringify(fullManifest,null,2);
      const full={...base,files:fullFiles,manifest:fullManifest,visualPaths:[]};
      const incomplete=captured.receipt.status==='unavailable'||evidence.receipt.status==='unavailable'||figures.evidence?.complete===false;
      if(incomplete)pending=null;
      return {...full,prepare:incomplete?prepare:()=>Promise.resolve(full)};
    })().catch(error=>{pending=null;throw error;});
    return pending;
  }
  return deferVisuals?{...base,prepare}:prepare();
}
