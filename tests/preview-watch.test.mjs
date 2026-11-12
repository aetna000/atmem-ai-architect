import test from 'node:test';
import assert from 'node:assert/strict';
import {ignoredWorkspacePath} from '../vite.config.mjs';
test('preview changes are watched even when a workspace has .local in its parent path',()=>{
 for(const root of ['/repo','/repo/.local/frozen/preview','/Volumes/MEM0/.local/preview']){
  for(const file of ['src/main.jsx','src/journey-workspace.css','src/ComponentReview.jsx','vite.config.mjs'])assert.equal(ignoredWorkspacePath(root+'/'+file,root),false);
  for(const file of ['.local/cache/data','.venv/bin/python','.memory-venv/state','examples/output.zip'])assert.equal(ignoredWorkspacePath(root+'/'+file,root),true);
 }
});
