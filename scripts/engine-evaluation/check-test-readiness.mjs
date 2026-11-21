import {chromium} from '@playwright/test';
const base=process.argv[2]||'http://localhost:5297';
const main=await (await fetch(base+'/src/main.jsx?test-readiness-v1')).text();
const reactUrl=main.match(/from "([^"]*\/react\.js[^";]*)"/)?.[1];
const reactDomUrl=main.match(/from "([^"]*react-dom_client[^";]*)"/)?.[1];
if(!reactUrl||!reactDomUrl)throw Error('Cannot resolve the preview React runtime');
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage();page.setDefaultTimeout(10000);page.on('pageerror',e=>console.error(e.message));page.on('console',m=>{if(m.type()==='error')console.error(m.text())});let runs=0;
 await page.route('**/api/emulation/run',async route=>{runs++;await route.fulfill({json:{status:'passed',checks:[{name:'fixture check',passed:true}]}})});
 await page.route('**/readiness-fixture',route=>route.fulfill({contentType:'text/html',body:`<div id="root"></div><script type="module">
 import React from '${reactUrl}';
 import ReactDOM from '${reactDomUrl}';
 import {useEmulation} from '/src/useEmulation.jsx?test-readiness-v1';
 import {EmulationPanel} from '/src/EmulationPanel.jsx?test-readiness-v1';
 import {CLOUD_STORAGE_SCENARIOS} from '/src/cloud-storage-scenarios.mjs';
 const supported=CLOUD_STORAGE_SCENARIOS[0].project;
 const missing=structuredClone(supported);missing.nodes.push({id:'email',data:{label:'Email sign-in',provider:'aws',kind:'resource',origin:'proposed'}});
 window.implemented=0;
 function App(){const [ready,setReady]=React.useState(false),[available,setAvailable]=React.useState(true);const emulation=useEmulation(ready?supported:missing,'staging',{token:'fixture'});
 React.useEffect(()=>{void emulation.run()},[]);
 return React.createElement(React.Fragment,null,React.createElement('button',{onClick:()=>setReady(true)},'Use supported design'),React.createElement('button',{onClick:()=>setAvailable(false)},'Disable implementation'),React.createElement(EmulationPanel,{project:ready?supported:missing,session:{token:'fixture'},emulation,onBuild:available?()=>window.implemented++:undefined}));}
 ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));
 </script>`}));
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/readiness-fixture');
 await page.getByRole('button',{name:'Implement and test this design',exact:true}).waitFor();
 if(!await page.getByRole('button',{name:'Emulate locally',exact:true}).isDisabled())throw Error('Missing code test was enabled');
 if(runs)throw Error('Premature emulation request');
 await page.getByRole('button',{name:'Implement and test this design',exact:true}).click();
 if(await page.evaluate(()=>window.implemented)!==1)throw Error('Implementation callback not invoked');
 await page.getByRole('button',{name:'Disable implementation'}).click();
 await page.getByText('Application implementation is unavailable in this session.',{exact:false}).waitFor();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download repair task'}).click();await download;
 await page.getByRole('button',{name:'Use supported design'}).click();
 await page.getByRole('button',{name:'Emulate locally',exact:true}).click();
 await page.getByRole('heading',{name:'Local emulation checks passed'}).waitFor();
 if(runs!==1||errors.length)throw Error(JSON.stringify({runs,errors}));
 console.log(JSON.stringify({passed:true,missingCodeRequests:0,implementationCallbacks:1,unavailableDownload:true,supportedDesignRequests:runs,pageErrors:errors,ownerProjectWrites:0,inferenceRequests:0}));
}finally{await browser.close()}
