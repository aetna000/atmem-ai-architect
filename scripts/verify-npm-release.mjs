// A successful publish may be queued. Verify public availability and exact bytes before declaring success.
import fs from 'node:fs';
import path from 'node:path';
import {releaseChannel} from './npm-release-channel.mjs';
import {createHash} from 'node:crypto';
const artifact=process.argv[2];if(!artifact)throw Error('Supply the accepted atmem-architect-VERSION.tgz artifact.');
const version=path.basename(artifact).match(/^atmem-architect-(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\.tgz$/)?.[1];if(!version)throw Error('Unexpected release artifact name.');
const channel=releaseChannel(version);
const integrity='sha512-'+createHash('sha512').update(fs.readFileSync(artifact)).digest('base64');
const deadline=Date.now()+35*60*1000;
while(true){
 let document;
 try{const r=await fetch('https://registry.npmjs.org/@atmem%2farchitect?verify='+Date.now(),{headers:{'Cache-Control':'no-cache'},signal:AbortSignal.timeout(15000)});if(r.ok)document=await r.json();}catch{/* Publication remains pending during a registry transport outage. */}
 const published=document?.versions?.[version];
 if(published){
  if(published.dist?.integrity!==integrity)throw Error('Registry package differs from the accepted CI artifact.');
  if(document['dist-tags']?.[channel]!==version)throw Error(`Version is public, but ${channel} points elsewhere. Review before changing tags.`);
  console.log(JSON.stringify({name:'@atmem/architect',version,channel,integrity,verifiedAt:new Date().toISOString()}));break;
 }
 console.log(new Date().toISOString()+' · npm accepted '+version+'; public registry processing is still pending.');
 if(Date.now()>=deadline)throw Error('Registry processing exceeded the verification window. Do not resubmit this immutable version; inspect publisher notices.');
 await new Promise(resolve=>setTimeout(resolve,30000));
}
