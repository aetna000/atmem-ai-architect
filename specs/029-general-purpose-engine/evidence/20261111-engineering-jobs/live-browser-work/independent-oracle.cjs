const assert=require('node:assert/strict');
const {normalize,normalizeBatch}=require('./inventory-normalizer.cjs');
let checks=0;
for(const [value,unit,expected] of [[0,'g',0],[1,'g',1],[2,'kg',2000],[0.25,'kg',250]]){assert.equal(normalize(value,unit),expected);checks++;}
for(const [value,unit] of [[true,'g'],['2','g'],[-1,'g'],[NaN,'g'],[Infinity,'kg'],[1,'KG'],[1,'lb']]){assert.throws(()=>normalize(value,unit),TypeError);checks++;}
assert.deepEqual(normalizeBatch([]),[]);checks++;
assert.deepEqual(normalizeBatch([{value:1,unit:'kg'},{value:3,unit:'g'}]),[1000,3]);checks++;
assert.equal(normalizeBatch(Array.from({length:100},()=>({value:1,unit:'g'}))).length,100);checks++;
assert.throws(()=>normalizeBatch(Array.from({length:101},()=>({value:1,unit:'g'}))),RangeError);checks++;
console.log('INDEPENDENT_BROWSER_ARTIFACT_ORACLE_PASSED',checks);
