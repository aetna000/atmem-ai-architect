import test from'node:test';import assert from'node:assert/strict';import{applyGoogleQuote}from'../src/pricing.mjs';import{estimate,setProjectSize}from'../src/estimate.mjs';
const project={id:'reference-project',facts:[],nodes:[{id:'api',data:{provider:'gcp',service:'Cloud Run',label:'Museum tickets',config:{region:'To be selected'}}}],estimate:{projectSize:'small'}};
const quote={available:true,provider:'gcp',service:'cloud-run',currency:'USD',region:'us-central1',planningReference:true,source:'Google Cloud public pricing',url:'https://cloud.google.com/run/pricing',date:'2026-11-13',meters:{cpu:{price:.000024,unit:'vCPU-seconds'},memory:{price:.0000025,unit:'GiB-seconds'},requests:{price:.4,unit:'million requests'}},coverage:'Reference only; other charges excluded.'};
test('reference pricing calculates usage, preserves undecided region and stays partial',()=>{const next=applyGoogleQuote(project,project.nodes[0],quote),cost=estimate(next,new Date('2026-11-13'));assert.equal(next.nodes[0].data.config.region,'To be selected');assert.ok(Math.abs(cost.preciseExpected-.0545)<1e-10);assert.equal(cost.complete,false);assert.ok(cost.lines.every(l=>l.price.planningReference));const medium=setProjectSize(next,'medium'),recalculated=applyGoogleQuote(medium,medium.nodes[0],quote);assert.ok(Math.abs(estimate(recalculated,new Date('2026-11-13')).preciseExpected-.545)<1e-10);});
test('manual rates, chosen region and unexpected source are preserved',()=>{const manual={...project,estimate:{...project.estimate,details:[{id:'manual',componentId:'api',quantity:1,price:5}]}};assert.equal(applyGoogleQuote(manual,manual.nodes[0],quote),manual);const regional={...project,nodes:[{...project.nodes[0],data:{...project.nodes[0].data,config:{region:'australia-southeast1'}}}]};assert.equal(applyGoogleQuote(regional,regional.nodes[0],quote),regional);assert.equal(applyGoogleQuote(project,project.nodes[0],{...quote,url:'https://example.com'}),project);});

test('Iowa public storage rates use sourced GiB conversion and preserve chosen region and manual inputs',async()=>{
 const {applyPriceQuotes}=await import('../src/pricing.mjs');
 const p={id:'storage',nodes:[{id:'files',data:{provider:'gcp',label:'Cloud Storage',service:'Cloud Storage',config:{region:'us-central1'}}}],estimate:{projectSize:'small'}};
 const q={available:true,provider:'gcp',region:'us-central1',price:.000027397*730,currency:'USD',unit:'GiB-month',service:'Cloud Storage Standard / single-region',source:'Google Cloud public pricing',url:'https://cloud.google.com/storage/pricing',date:'2026-11-13',coverage:'730-hour month; operations excluded.'};
 const next=applyPriceQuotes(p,[q]);assert.ok(Math.abs(next.estimate.prices.files.price-q.price*1e9/(1024**3))<1e-12);assert.equal(next.nodes[0].data.config.region,'us-central1');
 const manual={...p,estimate:{...p.estimate,prices:{files:{price:1,source:'Owner quote'}}}};assert.equal(applyPriceQuotes(manual,[q]),manual);
 assert.equal(applyPriceQuotes({...p,nodes:[{...p.nodes[0],data:{...p.nodes[0].data,config:{region:'us-east4'}}}]},[q]).estimate.prices,undefined);
});

test('missing AWS placement produces one Choose region action for many Lambda nodes',async()=>{
 const {fetchPlanningPrices}=await import('../src/pricing.mjs');
 const nodes=[1,2,3].map(id=>({id:'lambda-'+id,data:{provider:'aws',service:'AWS Lambda',label:'Step '+id,config:{region:'To be selected'}}}));
 const result=await fetchPlanningPrices({token:'fixture'},{id:'missing-region',provider:'aws',nodes,decisions:[]});
 assert.equal(result.errors.length,1);assert.equal(result.errors[0].action,'choose-region');assert.match(result.errors[0].reason,/Choose an AWS region/);
});
test('pricing reuses accepted placement without replacing explicit per-node regions',async()=>{
 const {fetchPlanningPrices}=await import('../src/pricing.mjs'),original=globalThis.fetch,regions=[];
 globalThis.fetch=async(_url,options)=>{regions.push(JSON.parse(options.body).region);return {ok:false,json:async()=>({detail:'Synthetic unavailable quote'})}};
 try{
 const p={id:'accepted-region',provider:'aws',decisions:[{subject:'cloud.region',status:'Accepted',decision:'us-east-1'}],nodes:[{id:'one',data:{provider:'aws',service:'Lambda',label:'One',config:{region:'To be selected'}}},{id:'two',data:{provider:'aws',service:'Lambda',label:'Two',config:{region:'ap-southeast-2'}}}]};
 const result=await fetchPlanningPrices({token:'fixture'},p);assert.deepEqual(regions,['us-east-1','ap-southeast-2']);assert.equal(p.nodes[0].data.config.region,'To be selected');assert.equal(result.project.nodes[0].data.config.region,'us-east-1');
 }finally{globalThis.fetch=original}
});
