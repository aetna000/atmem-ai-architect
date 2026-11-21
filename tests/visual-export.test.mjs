import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {diagramSvg,specificationPdf} from '../src/visual-export.mjs';

test('SVG exports all coordinates, parent offsets and escaped user labels',()=>{
 const previous=globalThis.document;
 globalThis.document={createElement:()=>({getContext:()=>({font:'',measureText:t=>({width:t.length*7})})})};
 try{
  const result=diagramSvg({name:'<script>bad</script>',revision:1,nodes:[{id:'a',position:{x:-900,y:-300},data:{label:'<image onload="bad">',description:'A & B'}},{id:'b',parentId:'a',position:{x:5000,y:2000},data:{label:'Far offscreen node'}}],edges:[{source:'a',target:'b',label:'Data < & >'}]});
  assert.ok(result.width>5000);assert.ok(result.height>2000);
  assert.match(result.svg,/Far offscreen node/);assert.match(result.svg,/&lt;script&gt;/);assert.doesNotMatch(result.svg,/<script>|<image /);
 }finally{globalThis.document=previous;}
});
test('long specifications paginate with an embedded font and no JavaScript actions',()=>{
 const font=fs.readFileSync(new URL('../public/fonts/NotoSans-Regular.ttf',import.meta.url)).toString('base64');
 const bytes=specificationPdf('# Specification\n\n'+('REQ-001 — Réservé. '+ 'Long requirement '.repeat(100)+'\n\n').repeat(10),font);
 const text=Buffer.from(bytes).toString('latin1');
 assert.ok(bytes.length>1000);assert.ok(Number(text.match(/\/Count (\d+)/)?.[1])>1);assert.match(text,/\/FontFile2/);assert.doesNotMatch(text,/\/JavaScript/);
});
