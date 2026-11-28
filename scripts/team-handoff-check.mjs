// Exercise Delivery's actual download and open the extracted site with networking disabled.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {createServer} from 'node:net';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
import {unzipSync,strFromU8} from 'fflate';

const root=fileURLToPath(new URL('..',import.meta.url));
const out=path.resolve(process.argv[2]||path.join(root,'.local/team-handoff-check'));
await mkdir(out,{recursive:true});
async function inspectBrand(surface,{dark=false,preview=false}={}){
  const state=await surface.locator('.brand img').evaluate(async img=>{
    const doc=img.ownerDocument;
    await img.decode();
    await doc.fonts.ready;
    const heading=doc.querySelector('h1'),link=img.closest('a');
    return {
      source:img.currentSrc,artworkWidth:img.naturalWidth,visibleWidth:img.getBoundingClientRect().width,
      title:img.alt,home:link.href,credit:doc.querySelector('.credit a').href,
      stylesheet:doc.querySelector('link[rel=stylesheet]').href,icon:doc.querySelector('link[rel=icon]').href,
      bodyFont:getComputedStyle(doc.body).fontFamily,headingFont:getComputedStyle(heading).fontFamily,
      linkColor:getComputedStyle(link).color,fonts:[...doc.fonts].filter(face=>face.status==='loaded').map(face=>face.family.replace(/['"]/g,'')),
      focusColor:doc.querySelector('.focus-node')?getComputedStyle(doc.querySelector('.focus-node')).backgroundColor:null,
    };
  });
  assert.ok(state.artworkWidth>0&&state.visibleWidth>=100);
  assert.equal(state.title,'AtMem AI Architect');assert.equal(state.home,'https://atmem.ai/');
  assert.equal(state.credit,'https://x.com/lostonwww');
  assert.match(state.source,preview?/^blob:/:dark?/\/assets\/atmem-on-dark\.svg$/:/\/assets\/atmem-on-light\.svg$/);
  assert.match(state.stylesheet,preview?/^blob:/:/\/assets\/handoff\.css$/);
  assert.match(state.icon,preview?/^blob:/:/\/assets\/favicon\.svg$/);
  assert.match(state.bodyFont,/^["']?DM Sans/);assert.match(state.headingFont,/^["']?Manrope/);
  assert.deepEqual(state.fonts.sort(),['DM Sans','Manrope']);
  assert.equal(state.linkColor,dark?'rgb(243, 162, 180)':'rgb(135, 59, 80)');
  if(state.focusColor!==null)assert.equal(state.focusColor,'rgb(243, 162, 180)');
}
let server,browser,base=process.env.ATMEM_TEAM_TEST_URL;
try{
  if(!base){
    const probe=createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));
    const port=probe.address().port;await new Promise(r=>probe.close(r));base='http://127.0.0.1:'+port;
    server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{cwd:root,stdio:'ignore'});
    for(let i=0;i<100;i++){if(await fetch(base).then(r=>r.ok,()=>false))break;await new Promise(r=>setTimeout(r,100));}
  }
  const chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  browser=await chromium.launch(existsSync(chrome)?{executablePath:chrome}:{});
  const page=await browser.newPage({viewport:{width:1440,height:960}});
  const errors=[],external=[],compressionWorkers=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('worker',worker=>{if(worker.url().includes('handoff-zip'))compressionWorkers.push(worker.url());});
  const installed=Boolean(process.env.ATMEM_TEAM_MODULE_TEST_URL);
  const savedProject=process.env.ATMEM_TEAM_PROJECT_FILE;
  if(!installed){
    await page.route('**/api/**',r=>r.fulfill({json:{status:'disabled',available:false,projects:[],bin:[],events:[]}}));
    await page.route('**/api/session',r=>r.fulfill({json:{token:'test',providers:{},status:'local-sidecar'}}));
  }
  await page.goto(base);
  if(installed&&!savedProject){
    await page.getByRole('button',{name:'More',exact:true}).click();
    await page.getByRole('menuitem',{name:'Open DNS handoff example'}).click();
  }else{
    await page.locator('#project-file-input').setInputFiles(savedProject||path.join(root,'examples/nextdns/project.json'));
    const delivery=page.getByRole('tab',{name:/Delivery/});
    if(!await delivery.isVisible())await page.locator('.drawing-journey-menu>summary').click();
    await delivery.click();
  }
  const previewStart=Date.now();
  await page.getByRole('button',{name:'Preview handoff website'}).click();
  await page.locator('dialog[open] iframe[src^="blob:"]').waitFor({timeout:60000});
  const preview=page.frameLocator('iframe[title="Handoff website pages"]');
  try{
    await preview.getByRole('heading',{name:'NextDNS-style DNS platform',exact:true}).waitFor({timeout:60000});
  }catch(error){
    const messages=await page.locator('[role=alert], .toast, dialog[open] header').allInnerTexts();
    throw Error('Handoff preview did not open. '+messages.join(' · ')+' · '+errors.join(' · '),{cause:error});
  }
  const previewMs=Date.now()-previewStart;
  await inspectBrand(preview,{preview:true});
  await preview.getByRole('link',{name:'Diagrams',exact:true}).click();
  assert.ok(await preview.locator('#diagrams').isVisible());
  assert.ok(await preview.locator('.sheet[open] img').evaluate(async img=>{await img.decode();return img.naturalWidth>0;}));
  await preview.getByRole('link',{name:'Project files',exact:true}).click();
  await preview.getByRole('link',{name:/Policy publisher/}).click();
  await preview.getByRole('heading',{name:'Policy publisher',exact:true}).waitFor();
  await inspectBrand(preview,{preview:true});
  await preview.getByRole('link',{name:'← Project build plan'}).first().click();
  await preview.getByRole('heading',{name:'Build plan',exact:true}).waitFor();
  await page.getByRole('button',{name:'Close preview'}).click();
  const downloadStart=Date.now(),wait=page.waitForEvent('download',{timeout:90000});
  await page.getByRole('button',{name:'Download team handoff',exact:true}).click();
  const download=await wait,zipPath=path.join(out,download.suggestedFilename());await download.saveAs(zipPath);
  const downloadMs=Date.now()-downloadStart;
  assert.ok(compressionWorkers.length>=2,'large downloads use background compression');
  const bytes=await readFile(zipPath),files=unzipSync(bytes),site=path.join(out,'website');
  for(const [name,data] of Object.entries(files)){
    const dest=path.resolve(site,name);assert.ok(dest.startsWith(site+path.sep));
    await mkdir(path.dirname(dest),{recursive:true});await writeFile(dest,data);
  }
  const inner=unzipSync(files['engineering/project-package.zip']),json=name=>JSON.parse(strFromU8(inner[name]));
  const manifest=json('manifest.json'),audit=json('diagram-readability.json');
  if(savedProject){
    const previous=JSON.parse(await readFile(savedProject,'utf8')),current=json('project.atmem-ai-architect.json');
    for(const key of ['id','name','revision'])assert.equal(current.meta[key],previous.meta[key],key);
    for(const key of ['design','requirements','decisions','assumptions','openQuestions','extensions'])assert.deepEqual(current[key],previous[key],key);
  }
  assert.equal(audit.pages.length,9);assert.ok(audit.pages.every(p=>p.passed));
  assert.equal(json('qualification/acceptance.json').length,10);
  for(const [name,{sha256}] of Object.entries(manifest.fileDigests))assert.equal(createHash('sha256').update(inner[name]).digest('hex'),sha256,name);
  const fixturePage=installed?await browser.newPage():page;
  if(installed)await fixturePage.goto(process.env.ATMEM_TEAM_MODULE_TEST_URL);
  const fallback=await fixturePage.evaluate(async()=>{
    const {renderProjectScenes}=await import('/src/architecture-scene-export.jsx');
    const node=id=>({id,type:'resource',position:{x:0,y:0},data:{label:id,provider:'tools',kind:'tool'}});
    const p={name:'Freight dispatch',revision:1,nodes:[node('Intake'),node('Freight')],edges:[]};
    const before=JSON.stringify(p);
    const strict=await renderProjectScenes(p).then(()=>false,e=>e.message.includes('layout issues'));
    const alt=await renderProjectScenes(p,{allowConnectionSheets:true});
    const receipt=JSON.parse(alt.files['diagram-readability.json']).pages[0];
    return {strict,presentation:receipt.presentation,savedLayoutPassed:receipt.passed,unchanged:JSON.stringify(p)===before,
      both:alt.board.svg.includes('Intake')&&alt.board.svg.includes('Freight')};
  });
  assert.deepEqual(fallback,{strict:true,presentation:'connections',savedLayoutPassed:false,unchanged:true,both:true});
  const sourceMedia=await fixturePage.evaluate(async()=>{
    const {teamHandoffFiles}=await import('/src/team-handoff.mjs');
    const {captureDesignDocuments}=await import('/src/design-documents.mjs');
    const encode=text=>new TextEncoder().encode(text);
    const source='<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40"><rect width="80" height="40" fill="green"/></svg>';
    const guide='# Survey guide\n\n![Floor plan](../images/plan.svg)\n\n![Damaged scan](../images/damaged.png)\n\n[Bay photo](missing.jpg)';
    const docs=captureDesignDocuments({'docs/survey.md':encode(guide)},'fixture','c'.repeat(64),'d'.repeat(64));
    const project={id:'survey',name:'Freight survey',revision:1,nodes:[],edges:[],extensions:{architectureDocuments:docs}};
    const files=await teamHandoffFiles({project,files:{'images/plan.svg':encode(source),'images/damaged.png':Uint8Array.of(137,80,78,71,13,10,26,10)}});
    const body=new DOMParser().parseFromString(files['documents/survey-guide.html'],'text/html');
    const png=files['source-images/floor-plan.png'],image=await createImageBitmap(new Blob([png],{type:'image/png'}));
    const result={decoded:[image.width,image.height],visibleImages:body.querySelectorAll('img.source-image').length,missing:body.querySelectorAll('.image-gap').length,
      named:files['index.html'].includes('Bay photo')&&files['index.html'].includes('Damaged scan'),rasterizedSvg:Object.hasOwn(files,'source-images/floor-plan.png')};
    image.close();return result;
  });
  assert.deepEqual(sourceMedia,{decoded:[80,40],visibleImages:1,missing:2,named:true,rasterizedSvg:true});
  const context=await browser.newContext({offline:true,colorScheme:'light',viewport:{width:1440,height:960}});
  const reader=await context.newPage();reader.on('pageerror',e=>errors.push(e.message));
  reader.on('request',r=>{if(/^https?:/i.test(r.url()))external.push(r.url());});
  const html=Object.keys(files).filter(n=>n.endsWith('.html')),index=pathToFileURL(path.join(site,'index.html')).href;
  assert.equal(html.filter(name=>name.startsWith('work-orders/')).length,11);
  let links=0,images=0;
  for(const name of html){
    await reader.goto(pathToFileURL(path.join(site,name)).href);
    await inspectBrand(reader);
    const resources=await reader.evaluate(async()=>{
      const images=[...document.images];await Promise.all(images.map(i=>{i.loading='eager';return i.decode();}));
      return {links:[...document.querySelectorAll('a[href]')].map(a=>a.href),images:images.filter(i=>!i.closest('.brand')).map(i=>({url:i.src,width:i.naturalWidth,height:i.naturalHeight}))};
    });
    for(const href of resources.links){
      if(!href.startsWith('file:'))continue;
      const url=new URL(href),dest=fileURLToPath(url);
      assert.ok(dest.startsWith(site+path.sep)&&existsSync(dest),href);links++;
      if(url.hash){const target=await readFile(dest,'utf8');assert.ok(target.includes('id="'+decodeURIComponent(url.hash.slice(1))+'"'),href);}
    }
    for(const i of resources.images){assert.ok(i.width>0&&i.height>0,i.url);images++;}
  }
  const metrics=[];
  for(const width of [1440,768,390,320]){
    await reader.setViewportSize({width,height:width>800?960:844});await reader.goto(index);
    await reader.screenshot({path:path.join(out,'overview-'+width+'.png')});
    for(const section of ['overview','diagrams','scope','build','operations','evidence','files']){
      await reader.locator('nav a[href="#'+section+'"]').click();
      assert.ok(await reader.locator('#'+section).isVisible(),section);
      assert.equal(await reader.locator('.view:visible').count(),1);
      assert.ok(await reader.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),section+' overflow at '+width);
    }
    metrics.push({width,sections:7,overflow:false});
  }
  await reader.setViewportSize({width:1440,height:960});
  await reader.emulateMedia({colorScheme:'dark'});await reader.goto(index);
  await inspectBrand(reader,{dark:true});await reader.screenshot({path:path.join(out,'overview-dark.png')});
  await reader.emulateMedia({media:'print',colorScheme:'dark'});await reader.reload();await inspectBrand(reader);
  assert.equal(await reader.locator('.view:visible').count(),7);
  await reader.emulateMedia({media:'screen',colorScheme:'light'});
  await reader.setViewportSize({width:1440,height:960});await reader.goto(index+'#diagrams');
  const sequence=reader.locator('.sheet').filter({hasText:'Allowed lookup sequence'});
  await sequence.locator(':scope > summary').click();await sequence.locator('img').scrollIntoViewIfNeeded();
  assert.ok(await sequence.locator('img').isVisible());await sequence.getByRole('checkbox').check();
  assert.equal(await sequence.getByRole('checkbox').isChecked(),true);
  await sequence.getByRole('checkbox').uncheck();await reader.screenshot({path:path.join(out,'sequence.png')});
  await reader.goto(index+'#files');await reader.getByRole('link',{name:/Policy publisher/}).click();
  assert.equal(await reader.getByRole('heading',{level:1}).innerText(),'Policy publisher');
  await reader.getByRole('link',{name:'← Project build plan'}).first().click();assert.ok(await reader.locator('#build').isVisible());
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  const entry=savedProject?'Existing project, imported into installed candidate':installed?'Installed example menu with local backend':'Imported project file';
  const result={entry,zip:download.suggestedFilename(),sha256:createHash('sha256').update(bytes).digest('hex'),archiveBytes:bytes.length,engineeringFiles:Object.keys(inner).length,
    verifiedPayloadDigests:Object.keys(manifest.fileDigests).length,readerFiles:Object.keys(files).length,htmlPages:html.length,localLinks:links,decodedImages:images,
    branding:{offlinePages:html.length,previewPages:2,fonts:['DM Sans','Manrope'],light:true,dark:true,print:true,accent:'#F3A2B4'},
    nativeLayoutChecks:audit.pages.map(p=>({name:p.name,issues:p.issues.length})),previewNavigation:true,previewMs,downloadMs,compressionWorkers:compressionWorkers.length,unreadableLayout:fallback,sourceMedia,viewports:metrics,offlineNetworkRequests:external.length,browserErrors:errors.length};
  await writeFile(path.join(out,'review.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}finally{await browser?.close();server?.kill();}
