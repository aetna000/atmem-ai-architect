import test from 'node:test';import assert from 'node:assert/strict';import {relativeLinkReport} from '../scripts/receiving-links.mjs';
test('receiving links resolve within the package and ignore external/anchor links',()=>{
 const report=relativeLinkReport({'docs/README.md':'[Draft](../architecture.canvas.json) [Index](sub/) [Web](https://example.com) [Part](#header)','architecture.canvas.json':'{}','docs/sub/plan.md':'Plan'});assert.equal(report.checked,2);assert.deepEqual(report.missing,[]);
});
test('missing original drafts, escaped links and prototype names are not false passes',()=>{
 const report=relativeLinkReport({'README.md':'[Draft](architecture.canvas.json) [Escape](../private.md) [Missing](constructor)'});assert.equal(report.missing.length,3);assert.equal(report.missing[1].reason,'outside_package');
});
