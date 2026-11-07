import test from 'node:test';
import assert from 'node:assert/strict';
import {ragProject} from './fixtures/rag-project.mjs';
import {terraformSketch} from '../src/terraform.mjs';
test('local source contracts export their runner but cannot masquerade as verified vendor production integrations',()=>{
 const p=ragProject();p.nodes.push({id:'sharepoint',position:{x:0,y:0},data:{kind:'resource',label:'SharePoint contract fixture',service:'Microsoft SharePoint',provider:'tools',origin:'existing',binding:'normalized-source-contract'}});p.edges.push({id:'sync',source:'sharepoint',target:'catalog',integration:'source-catalog-sync'});
 const staging=terraformSketch(p),production=terraformSketch(p,'production');
 assert.ok(staging['connectors/connector_cli.py']);assert.ok(staging['connectors/CONTRACT.md'].includes('not native Microsoft Graph'));
 assert.deepEqual(JSON.parse(staging['main.tf.json']).locals.unfinished_work,[]);
 assert.ok(JSON.parse(production['main.tf.json']).locals.unfinished_work.some(g=>g.startsWith('native-vendor-integration-unverified-')));
});
