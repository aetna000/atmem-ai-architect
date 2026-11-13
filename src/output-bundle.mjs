import {verifiedReceipt} from './validation-receipt.mjs';
import {deliveryPack} from './delivery.mjs';
export const VISUAL_PATHS=['spec-kit/implementation-spec.pdf','specification.pdf','diagram.svg','diagram.png','diagram.pdf'];
export async function outputBundle(project,run,environment,checks,{deferVisuals=false}={}){
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
      const {visualFiles}=await import('./visual-export.mjs');
      const fullFiles={...files,...await visualFiles(snapshot,files['specification.md'],files['spec-kit/implementation-spec.md'])};
      const fullManifest={...manifest,files:Object.keys(fullFiles)};
      fullFiles['manifest.json']=JSON.stringify(fullManifest,null,2);
      const full={...base,files:fullFiles,manifest:fullManifest,visualPaths:[]};
      return {...full,prepare:()=>Promise.resolve(full)};
    })().catch(error=>{pending=null;throw error;});
    return pending;
  }
  return deferVisuals?{...base,prepare}:prepare();
}
