import test from 'node:test';
import assert from 'node:assert/strict';
import {projectIdFromUrl} from '../src/project-links.mjs';
test('project links accept only the local project store identifier contract',()=>{
 assert.equal(projectIdFromUrl('http://127.0.0.1:5190/?project=qualification-storage-live'),'qualification-storage-live');
 for(const value of ['http://localhost/?project=../../private','http://localhost/?project=x','http://localhost/','not a URL'])assert.equal(projectIdFromUrl(value),null);
});
