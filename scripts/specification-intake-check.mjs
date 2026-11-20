// Browser routing regression using fixture providers. No credentials or inference required.
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';

const base = process.env.ATMEM_WORKFLOW_URL || 'http://127.0.0.1:5195';
const browser = await chromium.launch();
try {
  for (const [provider, width] of [['claude-code',1440], ['gemini-cli',390]]) {
    const page = await browser.newPage({viewport:{width,height:900}});
    const requests = [], native = [];
    await page.addInitScript(provider => localStorage.setItem('atforma-connection-v1',
      JSON.stringify({provider,model:'fixture-model'})), provider);
    await page.route('**/api/**', async route => {
      const endpoint = new URL(route.request().url()).pathname;
      if (endpoint === '/api/architect') requests.push(route.request().postDataJSON());
      if (/\/engineering\/(create|start|steer)$/.test(endpoint)) native.push(endpoint);
      const responses = {
        '/api/session': {token:'fixture',engineeringEnabled:true,status:'local-sidecar',providers:{[provider]:{installed:true,available:true,signedIn:true}}},
        '/api/architect': {message:'Reviewed both files.',contextUsed:[]},
        '/api/design-sources': {detail:'Source archive unavailable'},
      };
      await route.fulfill({status:endpoint === '/api/design-sources' ? 503 : 200,
        json:responses[endpoint] || {sessions:[],projects:[],bin:[],saved:true}});
    });
    await page.goto(base);
    await page.getByRole('button',{name:'Dismiss welcome card'}).click();
    const chooser = page.waitForEvent('filechooser');
    await page.getByRole('button',{name:'Upload specification',exact:true}).click();
    const documents = ['Keep processing on-premises.', 'Preserve the existing interface.'];
    await (await chooser).setFiles(documents.map((value,i)=>({name:'spec-'+i+'.md',mimeType:'text/markdown',buffer:Buffer.from(value)})));
    await page.getByText('Reviewed both files.',{exact:true}).waitFor();
    assert.equal(requests.length,1);
    const [request] = requests;
    assert.equal(request.provider,provider);
    assert.equal(request.model,'fixture-model');
    assert.deepEqual(request.attachments.map(file=>Buffer.from(file.data,'base64').toString()),documents);
    assert.deepEqual(native,[]);
    console.log(provider,width,'upload passed with archive unavailable');
    await page.close();
  }
} finally { await browser.close(); }
