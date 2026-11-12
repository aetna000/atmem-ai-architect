import test from 'node:test';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {identityToken,resourceAddress,assertDistinctIdentifiers} from '../src/identifiers.mjs';import {deliveryUnitName} from '../src/terraform-composition.mjs';import {compositionFixture} from '../scripts/engine-evaluation/composition-fixtures.mjs';import {terraformSketch} from '../src/terraform.mjs';
test('short accepted addresses are unchanged; long Unicode uses the standard digest without losing the original identity',()=>{
 for(const value of ['invoice','µ','x'.repeat(124)])assert.equal(identityToken(value),Buffer.from(value).toString('hex'));
 for(const value of ['測'.repeat(100),'😀'.repeat(100),'x'.repeat(125)]){const token=identityToken(value);assert.equal(token,'d'+createHash('sha256').update(value).digest('hex'));assert.equal(token.length%2,1);assert(Buffer.byteLength(deliveryUnitName(value))<255);assert(Buffer.byteLength(resourceAddress(value))<255);}
 assert.notEqual(identityToken('é'.repeat(100)),identityToken('e\u0301'.repeat(100)));
 assert.throws(()=>identityToken('\ud800'),/no characters were replaced/);
});
test('identity collisions and duplicates stop generation without overwriting scope',()=>{
 assert.throws(()=>assertDistinctIdentifiers(['first','second'],()=> 'collision'),/namespace collision/);assert.throws(()=>assertDistinctIdentifiers(['same','same']),/Duplicate/);assert.doesNotThrow(()=>assertDistinctIdentifiers(['é'.repeat(100),'e\u0301'.repeat(100)]));
});
test('accepted 100-character Unicode node IDs retain complete mappings in physically bounded module/application paths',()=>{
 const p=compositionFixture('gcp'),id='測'.repeat(100),old=p.nodes.find(n=>n.data.implementation==='invoice-workflow').id;p.nodes.find(n=>n.id===old).id=id;for(const e of p.edges){if(e.source===old)e.source=id;if(e.target===old)e.target=id;}for(const need of p.needs)need.links=need.links.map(v=>v===old?id:v);
 const files=terraformSketch(p),manifest=JSON.parse(files['composition.json']);assert(manifest.units.some(u=>u.id===id));for(const path of Object.keys(files))for(const part of path.split('/'))assert(Buffer.byteLength(part)<=255,path);assert.deepEqual(JSON.parse(files['generation-quality.json']).fatalFindings,[]);
});
