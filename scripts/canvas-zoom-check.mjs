// Browser regression for wheel, trackpad and two-contact zoom on the shared drawing canvas.
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
import {toProjectFile} from '../src/project-file.mjs';
import {addDiagram, emptyDiagramModel} from '../src/architecture-diagrams.mjs';

const {model,view} = addDiagram(emptyDiagramModel(), 'context', 'Context page', true);
const project = toProjectFile({
  id: 'zoom-regression-project', version: 1, revision: 1, name: 'Clinic referral', provider: 'tools',
  nodes: ['Intake','Review'].map((label, index) => ({
    id: 'node-' + index, type: 'resource', position: {x: 300 * index, y: 50},
    data: {label, kind: 'resource', provider: 'tools', description: label},
  })),
  edges: [], extensions: {architectureDiagrams: model},
});
const browser = await chromium.launch(process.env.ATMEM_ARCHITECT_BROWSER_BIN
  ? {executablePath: process.env.ATMEM_ARCHITECT_BROWSER_BIN} : {channel:'chrome'});
try {
  const page = await browser.newPage({viewport: {width: 1440, height: 900}, hasTouch: true});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/**', route => route.fulfill({json: route.request().url().endsWith('/api/session')
    ? {token:'fixture',status:'local-sidecar',providers:{}} : {status:'disabled',projects:[],bin:[],models:[],saved:true}}));
  await page.goto(process.env.ATMEM_ARCHITECT_BROWSER_URL || 'http://127.0.0.1:5174/');
  await page.locator('#project-file-input').setInputFiles({name:'clinic.json', mimeType:'application/json', buffer:Buffer.from(JSON.stringify(project))});
  const canvas = page.getByLabel('Architecture board', {exact:true});
  const node = canvas.getByRole('button', {name:'Intake',exact:true});
  await node.waitFor();
  await page.waitForTimeout(650); // Allow the Board's initial fit to finish.
  const before = await node.boundingBox();
  const cursor = {x:before.x + before.width * .4, y:before.y + before.height * .6};
  await page.mouse.move(cursor.x,cursor.y);
  const width = async () => (await node.boundingBox()).width;
  async function checkWheel(direction) {
    const previous = await width();
    await page.mouse.wheel(0, direction * -100);
    await page.waitForFunction(({previous,direction}) => {
      const rect = document.querySelector('[aria-label="Architecture board"] [aria-label="Intake"]').getBoundingClientRect();
      return direction * (rect.width - previous) > 3;
    }, {previous,direction}, {timeout:3000});
    const box = await node.boundingBox();
    assert(Math.abs(box.x + .4 * box.width - cursor.x) < 2);
    assert(Math.abs(box.y + .6 * box.height - cursor.y) < 2);
  }
  await checkWheel(1);
  await checkWheel(-1);
  const client = await page.context().newCDPSession(page);
  for (const gestureSourceType of ['mouse', 'touch']) {
    for (const factor of [1.35, .78]) {
      const initial = await width();
      await client.send('Input.synthesizePinchGesture', {
        x:Math.round(cursor.x), y:Math.round(cursor.y), scaleFactor:factor, gestureSourceType, relativeSpeed:260,
      });
      await page.waitForTimeout(120);
      assert((factor > 1 ? 1 : -1) * (await width() - initial) > 3, gestureSourceType + ' pinch ' + factor);
      assert.equal(await page.evaluate(() => visualViewport.scale), 1);
    }
  }
  assert.equal(await page.getByRole('complementary',{name:'Selected diagram record'}).isVisible(),false);
  // Exercise WebKit's cumulative gesture event contract independently of Ctrl+wheel.
  const initial = await width();
  await canvas.evaluate((element,point) => {
    for (const [name,scale] of [['gesturestart',1],['gesturechange',1.1],['gesturechange',1.3],['gestureend',1.3]]) {
      const event = Object.assign(new Event(name,{bubbles:true,cancelable:true}),{clientX:point.x,clientY:point.y,scale});
      element.dispatchEvent(event);
      if(!event.defaultPrevented)throw new Error('Unclaimed gesture');
    }
  },cursor);
  assert(Math.abs(await width() / initial - 1.3) < .03);
  // A completed pinch releases the graph for ordinary selection.
  await node.click();
  const inspector = page.getByRole('complementary',{name:'Selected diagram record'});
  await inspector.waitFor();
  await inspector.getByRole('button',{name:'Close diagram source'}).click();
  const after = await width();
  await page.getByRole('complementary',{name:'Board library'}).hover();
  await page.mouse.wheel(0,200);
  await page.waitForTimeout(100);
  assert.equal(await width(),after);
  await page.getByLabel('Go to page').filter({visible:true}).selectOption('view/' + view.id);
  const diagram = page.getByLabel('Context page',{exact:true}).filter({has:page.locator('svg')});
  const record = diagram.getByRole('button').first();
  await record.hover();
  const pageWidth = (await record.boundingBox()).width;
  await page.mouse.wheel(0,-110);
  await page.waitForTimeout(150);
  assert((await record.boundingBox()).width > pageWidth);
  // A large graph must start at readable size. Only the explicit Fit control
  // may shrink it to a miniature overview; import and layout must not do so.
  const large=structuredClone(project);large.meta.id='large-zoom-regression';
  large.design.nodes[1].position.x=5000;
  await page.locator('#project-file-input').setInputFiles({name:'large.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(large))});
  const largeNode=page.getByLabel('Architecture board',{exact:true}).getByRole('button',{name:'Intake',exact:true});
  await largeNode.waitFor();await page.waitForTimeout(900);
  const readableWidth=(await largeNode.boundingBox()).width;
  assert(readableWidth>=200,'Automatic layout must preserve readable labels');
  const first=await largeNode.boundingBox();assert(first.x>=0&&first.x+first.width<=1440,'Readable initial focus must contain a component');
  await page.getByRole('button',{name:'Fit',exact:true}).click();await page.waitForTimeout(400);
  assert((await largeNode.boundingBox()).width<readableWidth,'Explicit Fit still provides the whole graph');
  assert.deepEqual(errors,[]);
  console.log('Wheel anchoring, trackpad and touch pinch, WebKit gesture events, sidebar scrolling and diagram page zoom passed.');
} finally {
  await browser.close();
}
