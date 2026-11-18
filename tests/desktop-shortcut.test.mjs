import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createDesktopShortcut} from '../cli/desktop-shortcut.mjs';

test('Mac shortcut survives npx cache removal and preserves paths with shell characters', () => {
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'architect-shortcut-'));
 try {
  const npmCli=path.join(folder,'npm-cli.js'), receipt=path.join(folder,'args.json');
  fs.writeFileSync(npmCli,'require("fs").writeFileSync(process.env.SHORTCUT_RECEIPT,JSON.stringify(process.argv.slice(2)))');
  const home=path.join(folder,"projects ' $HOME `echo wrong`");
  const target=createDesktopShortcut({version:'0.2.5-beta.1',home,port:5174,platform:'darwin',desktop:folder,npmCli});
  const result=spawnSync('/bin/sh',[target],{env:{...process.env,SHORTCUT_RECEIPT:receipt}});
  assert.equal(result.status,0,result.stderr?.toString());
  assert.deepEqual(JSON.parse(fs.readFileSync(receipt)),['exec','--yes','--package','@atmem/architect@0.2.5-beta.1','--','atmem-architect','--data-dir',home,'--port','5174']);
 } finally {fs.rmSync(folder,{recursive:true,force:true});}
});
