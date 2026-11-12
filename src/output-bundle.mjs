import {verifiedReceipt} from './validation-receipt.mjs';
import {deliveryPack} from './delivery.mjs';
export async function outputBundle(project,run,environment,checks){
  const snapshot=structuredClone(project);
  const files=deliveryPack(snapshot,run,environment);
  const {visualFiles}=await import('./visual-export.mjs');
  Object.assign(files,await visualFiles(snapshot,files['specification.md'],files['spec-kit/implementation-spec.md']));
  if(checks){const terraform=Object.fromEntries(Object.entries(files).filter(([name])=>name.startsWith('terraform/')).map(([name,value])=>[name.slice(10),value]));const receipt=await verifiedReceipt(terraform,checks);if(receipt)files['terraform/validation-receipt.json']=JSON.stringify(receipt,null,2);}
  const manifest=JSON.parse(files['manifest.json']);manifest.files=Object.keys(files);
  files['manifest.json']=JSON.stringify(manifest,null,2);
  const slug=snapshot.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'atflow';
  return {project,files,manifest,filename:`${slug}-r${snapshot.revision}-delivery.zip`};
}
