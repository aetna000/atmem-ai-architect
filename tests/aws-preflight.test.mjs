import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {awsPreflightFiles} from '../src/aws-preflight.mjs';
test('account preflight catches low quotas, replacement reservations and preserves update capacity',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atmem-preflight-'));
 try{
 fs.writeFileSync(path.join(root,'preflight.py'),awsPreflightFiles()['preflight-aws.py']);
 const code=`import preflight
p=lambda before,after,actions:{"resource_changes":[{"type":"aws_lambda_function","change":{"before":{"reserved_concurrent_executions":before},"after":{"reserved_concurrent_executions":after},"actions":actions}}]}
assert preflight.concurrency_requirement(p(None,2,["create"]))==2
assert not preflight.check_concurrency(p(None,2,["create"]),{"ConcurrentExecutions":10,"UnreservedConcurrentExecutions":10})["passed"]
assert preflight.check_concurrency(p(None,2,["create"]),{"ConcurrentExecutions":110,"UnreservedConcurrentExecutions":110})["passed"]
assert preflight.concurrency_requirement(p(2,2,["update"]))==0
assert preflight.concurrency_requirement(p(2,3,["update"]))==1
assert preflight.concurrency_requirement(p(2,2,["delete","create"]))==2
try:preflight.concurrency_requirement(p(2,-1,["update"]))
except ValueError:pass
else:raise AssertionError("Unbounded configuration accepted")
`;
 fs.writeFileSync(path.join(root,'test.py'),code);
 const result=spawnSync(path.resolve('.venv/bin/python'),['test.py'],{cwd:root,env:{PATH:process.env.PATH},encoding:'utf8'});assert.equal(result.status,0,result.stderr);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
