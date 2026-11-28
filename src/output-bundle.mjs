import {architectureDiagramHandoff,architectureDiagramReview} from './architecture-diagram-handoff.mjs';
import {verifiedReceipt} from './validation-receipt.mjs';
import {deliveryPack} from './delivery.mjs';
export const VISUAL_PATHS=['spec-kit/implementation-spec.pdf','specification.pdf','diagram.svg','diagram.png','diagram.pdf'];
export async function outputBundle(project,run,environment,checks,{deferVisuals=false,session,prepareSources}={}){
  const snapshot=structuredClone(project);
  const files=deliveryPack(snapshot,run,environment);
  const diagrams=snapshot.extensions?.architectureDiagrams;
  if(diagrams?.views.length){
    files['architecture-handoff.md']=architectureDiagramHandoff(snapshot.name,snapshot.revision,diagrams);
    files['architecture-model.json']=JSON.stringify(diagrams,null,2);
    files['architecture-review.json']=JSON.stringify(architectureDiagramReview(snapshot.name,snapshot.revision,diagrams),null,2);
  }
  if(checks){const terraform=Object.fromEntries(Object.entries(files).filter(([name])=>name.startsWith('terraform/')).map(([name,value])=>[name.slice(10),value]));const receipt=await verifiedReceipt(terraform,checks);if(receipt)files['terraform/validation-receipt.json']=JSON.stringify(receipt,null,2);}
  const manifest=JSON.parse(files['manifest.json']);manifest.files=Object.keys(files);
  files['manifest.json']=JSON.stringify(manifest,null,2);
  const slug=snapshot.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'atflow';
  const base={project,snapshot,files,manifest,filename:`${slug}-r${snapshot.revision}-delivery.zip`,visualPaths:VISUAL_PATHS};
  const pending=new Map();
  async function prepare(team=false){
    if(!pending.has(team))pending.set(team,(async()=>{
      const sourceSession=(snapshot.extensions?.architectureDocuments||snapshot.extensions?.designSources?.some(source=>source.figureEvidence?.figures?.length))&&prepareSources?await prepareSources(project):session;
      const {attachReviewedDraftFiles}=await import('./reviewed-draft.mjs');
      const evidence=await attachReviewedDraftFiles(snapshot,files,{session:sourceSession});
      const {attachCapturedEvidenceFiles}=await import('./capture-download.mjs');
      const captured=await attachCapturedEvidenceFiles(snapshot,evidence.files,{session:sourceSession,sourceFile:'project.atmem-ai-architect.json'});
      const {attachSourceFigureFiles}=await import('./source-handoff.mjs');
      const figures=await attachSourceFigureFiles(snapshot,captured.files,{session:sourceSession});
      const {visualFiles}=await import('./visual-export.mjs');
      const {renderProjectScenes}=await import('./architecture-scene-export.jsx');
      const scenes=await renderProjectScenes(snapshot,{allowConnectionSheets:team});
      const fullFiles={...figures.files,...scenes.files,...await visualFiles(snapshot,files['specification.md'],files['spec-kit/implementation-spec.md'],scenes.board)};
      const fileDigests=Object.fromEntries(await Promise.all(Object.entries(fullFiles).filter(([name])=>name!=='manifest.json').map(async([name,content])=>{
        const bytes=typeof content==='string'?new TextEncoder().encode(content):content;
        const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(byte=>byte.toString(16).padStart(2,'0')).join('');
        return [name,{sha256:digest,bytes:bytes.byteLength}];
      })));
      const fullManifest={...manifest,files:Object.keys(fullFiles),fileDigests,hashBoundary:'Payload files only; manifest is excluded from its own hashes.',implementationExecutedByExport:false,deploymentExecutedByExport:false};
      fullFiles['manifest.json']=JSON.stringify(fullManifest,null,2);
      const full={...base,files:fullFiles,manifest:fullManifest,visualPaths:[]};
      const incomplete=captured.receipt.status==='unavailable'||evidence.receipt.status==='unavailable'||figures.evidence?.complete===false;
      if(incomplete)pending.delete(team);
      return {...full,prepare:()=>prepare(),prepareTeam:()=>prepare(true)};
    })().catch(error=>{pending.delete(team);throw error;}));
    return pending.get(team);
  }
  return deferVisuals?{...base,prepare:()=>prepare(),prepareTeam:()=>prepare(true)}:prepare();
}
