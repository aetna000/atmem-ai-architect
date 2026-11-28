import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {strToU8} from 'fflate';
import {deliveryPack} from '../src/delivery.mjs';
import {captureDesignDocuments} from '../src/design-documents.mjs';
import {designHandoffWebsite,teamHandoffFiles,verifyTeamLinks} from '../src/team-handoff.mjs';
import {connectionFigure,sequenceFigure} from '../src/handoff-drawings.mjs';
import {toProjectFile} from '../src/project-file.mjs';
import {createBlockHandoff,blockHandoffExportFiles} from '../src/block-handoff.mjs';
import {deriveRequirements} from '../src/derive.mjs';
import packageMetadata from '../package.json' with {type:'json'};
import provenance from '../docs/brand-source.json' with {type:'json'};

const node=(id,label,x)=>({id,type:'resource',position:{x,y:0},data:{kind:'tool',provider:'tools',label,origin:'existing',description:'Route delivery notices.'}});
const freight=()=>({id:'freight',version:1,revision:8,name:'Freight & dispatch',provider:'tools',requirements:'Track consignment notices.',
  nodes:[node('warehouse-a','Dock / intake',0),node('warehouse-b','Dock — intake',400),node('warehouse-c','配送',800)],
  edges:[{id:'notice',source:'warehouse-a',target:'warehouse-b',label:'Dispatch notice'}],needs:[],decisions:[],assumptions:[],openQuestions:[]});
const png=new Uint8Array(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jaksAAAAASUVORK5CYII=','base64'));

test('every reader ships the official artwork, licensed brand fonts and local theme assets',async()=>{
  const project=freight();
  project.extensions={architectureDocuments:captureDesignDocuments({'docs/guide.md':strToU8('# Loading guide\n\nCheck the dock.')},'fixture','c'.repeat(64),'d'.repeat(64))};
  const files=await teamHandoffFiles({project,files:deliveryPack(project)});
  const css=files['assets/handoff.css'];
  const artwork={
    'brand/atmem-horizontal-on-light.svg':'assets/atmem-on-light.svg',
    'brand/atmem-horizontal-on-dark.svg':'assets/atmem-on-dark.svg',
    'favicon.svg':'assets/favicon.svg',
  };
  for(const [name,expected] of Object.entries(provenance.handoffWebsite.verifiedAssets)){
    const bytes=readFileSync(new URL('../public/'+name,import.meta.url));
    assert.equal(createHash('sha256').update(bytes).digest('hex'),expected,name);
    if(artwork[name])assert.equal(files[artwork[name]],bytes.toString(),name);
    else assert.ok(css.includes('data:font/woff2;base64,'+bytes.toString('base64')),name);
  }
  for(const name of ['DM-Sans','Manrope']){
    const license=readFileSync(new URL('../public/fonts/'+name+'-OFL.txt',import.meta.url),'utf8');
    assert.ok(files['assets/font-licenses.txt'].includes(license),name);
  }
  for(const name of ['atmem-tokens.css','brand.css']){
    assert.ok(css.includes(readFileSync(new URL('../src/'+name,import.meta.url),'utf8')),name);
  }
  assert.doesNotMatch(css,/@import|url\(["']?https?:/i);
  const block=createBlockHandoff(JSON.stringify(toProjectFile(project)),'warehouse-a');
  const module=await teamHandoffFiles({project,files:blockHandoffExportFiles(block)},{blockIds:block.blockIds,focusId:block.blockId});
  assert.ok(files['documents/loading-guide.html']);
  for(const reader of [files,module]){
    for(const [name,body] of Object.entries(reader).filter(([name])=>name.endsWith('.html'))){
      const dir=name.includes('/')?'../assets/':'./assets/';
      for(const relative of ['atmem-on-light.svg','atmem-on-dark.svg','favicon.svg','handoff.css']){
        assert.ok(body.includes('"'+dir+relative+'"'),name+' links '+relative);
      }
      assert.match(body,/alt="AtMem AI Architect"/);
      assert.ok(body.includes('href="'+provenance.handoffWebsite.origin+'"'));
      assert.ok(body.includes('href="'+provenance.handoffWebsite.logoCredit+'"'));
    }
  }
  for(const missing of ['assets/atmem-on-dark.svg','assets/handoff.css','assets/favicon.svg']){
    const incomplete={...files};delete incomplete[missing];
    assert.throws(()=>verifyTeamLinks(incomplete),/Unresolved handoff link/);
  }
});
test('team filenames are readable, collision-safe and portable while the captured package stays byte-identical',async()=>{
  const project=freight(),archive=Uint8Array.of(8,9),raw=deliveryPack(project);
  const before=structuredClone(project),files=await teamHandoffFiles({project,files:raw},{archive});
  assert.equal(Object.keys(files)[0],'index.html');
  assert.equal(toProjectFile(project).meta.generator,'atmem-ai-architect '+packageMetadata.version);
  assert.deepEqual(Object.keys(files).filter(p=>p.startsWith('work-orders/')),['work-orders/dock-intake.html','work-orders/dock-intake-2.html','work-orders/配送.html']);
  assert.equal(files['engineering/project-package.zip'],archive);assert.deepEqual(project,before);
  assert.match(files['diagrams/component-connections.svg'],/Dispatch notice/);
  assert.match(files['index.html'],/Freight &amp; dispatch/);assert.match(files['index.html'],/Unpriced/);
  const bundle={project,files:raw};
  const prepared=designHandoffWebsite(bundle);
  assert.equal(designHandoffWebsite(bundle),prepared);
  const edited={...project,name:'Harbour dispatch',revision:9};
  assert.match((await designHandoffWebsite({project:edited,files:deliveryPack(edited)}))['index.html'],/Harbour dispatch/);
  assert.match((await prepared)['index.html'],/Freight &amp; dispatch/);
  assert.throws(()=>verifyTeamLinks({...files,'index.html':'<img src="./absent.png">'}),/Unresolved handoff link/);
  assert.throws(()=>verifyTeamLinks({...files,'index.html':'<a href="#absent">go<\/a>'}),/Unresolved handoff link/);
});
test('authored guides resolve nested and reference-style images and report missing pictures without phantom links',async()=>{
  const project=freight(),markdown='# Receiver guide\n\n![Dock photo][p]\n\n[p]: <../pictures/dock%20one.png>\n\n<img src="missing.png" alt="Missing bay">\n\n[Checklist](checklist.md)\n\n[View dock](../pictures/dock%20one.png)\n\n[Inspect manifest image](absent.jpg)\n\n<script>unsafe()</script>';
  project.extensions={architectureDocuments:captureDesignDocuments({'docs/guide.md':strToU8(markdown),'docs/checklist.md':strToU8('# Checklist\n\nCheck freight.')},'fixture','b'.repeat(64),'c'.repeat(64))};
  const raw={...deliveryPack(project),'pictures/dock one.png':png};
  const files=await teamHandoffFiles({project,files:raw});
  const guide=files['documents/receiver-guide.html'];
  assert.match(guide,/src="\.\.\/source-images\/dock-photo.png"/);assert.deepEqual(files['source-images/dock-photo.png'],png);
  assert.match(guide,/href="\.\.\/documents\/checklist.html"/);assert.match(guide,/Referenced image unavailable/);
  assert.doesNotMatch(guide,/<img[^>]+missing\.png|<script>/);assert.match(files['index.html'],/Missing bay/);
  assert.match(guide,/href="\.\.\/source-images\/dock-photo.png"/);assert.match(files['index.html'],/Inspect manifest image/);
  assert.equal(raw['docs/guide.md'],markdown);verifyTeamLinks(files);
});
test('a module assigns only its own work orders, with its external neighbour labelled in the diagram',async()=>{
  const project=freight(),handoff=createBlockHandoff(JSON.stringify(toProjectFile(project)),'warehouse-a');
  const files=await teamHandoffFiles({project,files:blockHandoffExportFiles(handoff)},{blockIds:handoff.blockIds,focusId:handoff.blockId});
  assert.deepEqual(Object.keys(files).filter(path=>path.startsWith('work-orders/')),['work-orders/dock-intake.html']);
  assert.match(files['diagrams/module-interfaces.svg'],/Dock — intake/);
  assert.doesNotMatch(files['index.html'],/配送/);assert.match(files['index.html'],/Assigned components/);
});
test('reader preserves repeated sequence messages, self-calls, return direction and unconnected elements',async()=>{
  const scene={name:'Route check',vertices:[{id:'a',name:'Intake'},{id:'b',name:'Dispatch'},{id:'c',name:'Reserve berth'}],
    wires:[{id:'s1',source:'a',target:'b',name:'Transmit'},{id:'s2',source:'b',target:'b',name:'Inspect'},{id:'s3',source:'b',target:'a',name:'Receipt',kind:'return'}]};
  const seq=sequenceFigure(scene).svg;assert.match(seq,/1. Transmit/);assert.match(seq,/2. Inspect/);assert.match(seq,/3. Receipt/);assert.match(seq,/h48v16h-48/);assert.match(seq,/stroke-dasharray="6 4"/);
  const sheet=connectionFigure(scene).svg;assert.match(sheet,/Reserve berth/);assert.match(sheet,/Receipt/);
  const none=await teamHandoffFiles({project:{...freight(),nodes:[],edges:[]},files:{}});
  assert.match(none['index.html'],/No components recorded/);assert.doesNotMatch(none['index.html'],/src="\.\/(?:diagrams|source-images)\//);
});
test('a data-only service receives a data location question grounded in its own processing',()=>{
  const project=freight();project.nodes[0].data.role='data';
  assert.doesNotMatch(deriveRequirements(project).find(r=>r.id==='drv-data-location').statement,/model requests/);
  project.nodes[1].data.role='llm';
  assert.match(deriveRequirements(project).find(r=>r.id==='drv-data-location').statement,/model requests/);
});
