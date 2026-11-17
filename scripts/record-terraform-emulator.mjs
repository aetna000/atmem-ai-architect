import {chromium} from '@playwright/test';import fs from 'node:fs';
// Run against a configured local backend/preview; records actual API responses.
const folder=process.argv[2]||'.local/terraform-emulator-video';fs.mkdirSync(folder,{recursive:true});
const b=await chromium.launch();const c=await b.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:folder,size:{width:1920,height:1080}}});
const p=await c.newPage();const events=[],marks={};let report=null;const start=Date.now();
p.on('pageerror',e=>events.push({error:e.message}));
p.on('response',async r=>{if(!r.url().includes('/api/terraform/emulate'))return;try{const data=await r.json();if(data.report)report=data.report;if(events.at(-1)?.state!==data.state||events.at(-1)?.events!==data.events?.length)console.log('Emulation',data.state,data.report?.status||data.events?.at(-1)?.stage||'');events.push({seconds:(Date.now()-start)/1000,status:r.status(),state:data.state,events:data.events?.length,reportStatus:data.report?.status});}catch{}});
try{
 await p.goto(process.env.ATMEM_EMULATOR_DEMO_URL||'http://127.0.0.1:5174/');await p.waitForTimeout(1500);
 await p.setInputFiles('#project-file-input','examples/aws/03-async-documents/history/2026-11-07T05-49-19.638Z/round-2/workspace.json');await p.waitForTimeout(2000);
 for(const label of ['Later','Dismiss welcome card','Switch to dark mode','Hide chat']){const x=p.getByRole('button',{name:label,exact:true});if(await x.count())await x.first().click();}
 await p.getByRole('button',{name:'Fit',exact:true}).click();await p.locator('.apply-launcher').click();await p.waitForTimeout(500);
 marks.ready=(Date.now()-start)/1000;await p.screenshot({path:folder+'/ready.png'});
 await p.getByRole('button',{name:'Run apply emulation',exact:true}).click();marks.run=(Date.now()-start)/1000;
 await p.waitForFunction(()=>/passed|failed|blocked|unavailable|not available/i.test(document.querySelector('.apply-dock h3')?.textContent||''),null,{timeout:1600000});
 marks.finished=(Date.now()-start)/1000;console.log(await p.locator('.apply-dock').innerText());
 if(!report)await p.waitForTimeout(1000);
 await p.screenshot({path:folder+'/finished.png'});
 await p.getByRole('button',{name:'Show details',exact:true}).click();await p.waitForTimeout(2000);
 if(report?.status!=='passed')throw Error('Live emulation did not pass: '+report?.status);
 const download=p.waitForEvent('download');await p.getByRole('button',{name:'Download apply report',exact:true}).click();await(await download).saveAs(folder+'/apply-report.json');
}catch(e){events.push({error:e.message});await p.screenshot({path:folder+'/error.png'});process.exitCode=1;}
finally{marks.end=(Date.now()-start)/1000;fs.writeFileSync(folder+'/browser-evidence.json',JSON.stringify({marks,events,report},null,2));await c.close();await b.close();}
