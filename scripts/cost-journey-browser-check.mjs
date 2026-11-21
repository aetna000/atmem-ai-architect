// Component browser fixtures, not native generation or provider pricing evidence.
import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createServer} from 'node:net';
fs.mkdirSync('.local/ui-cost-journey',{recursive:true});
fs.writeFileSync('.local/ui-cost-journey/index.html','<div id="root"></div><script type="module">\nimport React from \'react\';\nimport {createRoot} from \'react-dom/client\';\nimport {EstimateView} from \'/src/JourneyViews.jsx\';\nimport {ImplementationDelivery} from \'/src/ImplementationDelivery.jsx\';\nimport {estimate} from \'/src/estimate.mjs\';\nimport \'/src/style.css\';\nfunction App(){const [p,setP]=React.useState({id:\'fixture-project\',version:1,revision:1,name:\'Planning test\',nodes:[{id:\'store\',data:{kind:\'resource\',role:\'data\',provider:\'aws\',label:\'Storage\'},position:{x:0,y:0}}],edges:[]});return React.createElement(React.Fragment,null,React.createElement(EstimateView,{project:p,result:estimate(p),onChange:setP,onEstimate:()=>window.calls=(window.calls||0)+1}),React.createElement(ImplementationDelivery,{project:p,session:{token:\'fixture\',engineeringEnabled:true},onBuild:()=>window.builds=(window.builds||0)+1}));}createRoot(document.getElementById(\'root\')).render(React.createElement(App));\n</script>\n');
const socket=createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));
const base=`http://127.0.0.1:${port}`;
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'ignore'});
let browser;
try {
 for(let i=0;i<40;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,150));}
 browser=await chromium.launch({headless:true});
 for(const width of [1440,390]){
  const page=await browser.newPage({viewport:{width,height:950}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let captured=false;
  await page.route('**/api/**',route=>{const url=route.request().url();if(url.endsWith('/delivery')&&!captured)return route.fulfill({status:404,json:{detail:'Save or restore this project before opening its engineering job.'}});return route.fulfill({json:url.endsWith('/validators')?{validators:[],available:true}:url.endsWith('/validation/list')?{checks:[]}:{artifact:captured?{id:'artifact-fixture',sha256:'a'.repeat(64),files:[{path:'README.md',kind:'file'}],model:'fixture',effort:'high'}:null,canPackage:captured,relation:'matches_saved_design',session:{id:'session-fixture'}}});});
  await page.goto(base+'/.local/ui-cost-journey/index.html');
  await page.getByRole('button',{name:'Medium',exact:true}).click();
  assert.equal(await page.getByRole('button',{name:'Medium',exact:true}).getAttribute('aria-pressed'),'true');
  assert.equal(await page.evaluate(()=>window.calls),1);
  await page.getByText('Adjust usage assumptions and prices',{exact:true}).click();
  assert.match(await page.getByLabel('Data stored',{exact:true}).locator('..').innerText(),/100 GB · Medium planning assumption/);
  await page.getByLabel('Data stored',{exact:true}).fill('42');
  await page.getByRole('button',{name:'Large',exact:true}).click();
  assert.match(await page.getByLabel('Data stored',{exact:true}).locator('..').innerText(),/42 GB · entered/);
  await page.getByRole('button',{name:'Go to Review',exact:true}).click();
  assert.equal(await page.evaluate(()=>window.builds),1);
  assert.equal(await page.getByRole('button',{name:/Download/}).count(),0);
  captured=true;
  await page.getByRole('button',{name:'Refresh delivery',exact:true}).click();
  await page.getByRole('button',{name:'Download project package (ZIP)',exact:true}).waitFor();
  await page.getByText('Package files and source receipt',{exact:true}).click();
  assert.equal(await page.getByRole('button',{name:/Download/}).count(),1);
  assert.deepEqual(errors,[]);console.log(JSON.stringify({width,preset:true,explicitOverride:true,noPrematureDownload:true,errors}));await page.close();
 }
}finally{await browser?.close();server.kill('SIGTERM');}
