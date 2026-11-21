import {chromium} from '@playwright/test';
const base=process.argv[2]||'http://localhost:5285';
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage();const errors=[],failed=[],responses=[];let blockedWrites=0;
 page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>failed.push({url:r.url(),error:r.failure()?.errorText}));page.on('response',r=>{if(r.status()>=400)responses.push({url:r.url(),status:r.status()})});
 await page.route('**/api/**',async route=>{if(route.request().method()!=='GET'&&!new URL(route.request().url()).pathname.endsWith('/api/models')){blockedWrites++;return route.fulfill({status:503,json:{detail:'Read-only preview observation'}})}return route.continue()});
 await page.goto(base+'/',{waitUntil:'networkidle',timeout:20000}).catch(e=>errors.push(e.message));
 if(errors.length||failed.length||responses.length||!await page.locator('.react-flow').count())throw Error(JSON.stringify({errors,failed,responses}));
 console.log(JSON.stringify({errors,failed,responses,rootTextLength:(await page.locator('#root').innerText()).length,canvasCount:await page.locator('.react-flow').count(),blockedWrites}));
}finally{await browser.close()}
