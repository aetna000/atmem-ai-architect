"""Operator probe: real Chromium behind the unchanged named worker policy."""
import asyncio,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.codex_worker_policy import CodexWorkerClient,PROFILE
async def main():
 config=json.loads((ROOT/'.local/engineering-preview/operator-toolchain.json').read_text())
 browser=Path.home()/'Library/Caches/ms-playwright/chromium_headless_shell-1248'
 playwright=ROOT/'node_modules/playwright-core'
 output=ROOT/'.local/engine-product/worker-browser-probe';output.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='atm-browser-',dir='/tmp') as folder:
  workspace=Path(folder).resolve();script=workspace/'probe.mjs'
  script.write_text('''import {chromium} from MODULE;
const browser=await chromium.launch({headless:true,chromiumSandbox:true,executablePath:EXECUTABLE});
try {
 const page=await browser.newPage();
 await page.route('**/*',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><button id="go">Ready</button>'}));
 await page.goto('https://local-test.invalid/');
 if(await page.locator('#go').textContent()!=='Ready')throw Error('Browser did not execute');
 console.log('WORKER_BROWSER_EXECUTED');
}finally{await browser.close();}
'''.replace('MODULE',json.dumps(str(playwright/'index.mjs'))).replace('EXECUTABLE',json.dumps(str(browser/'chrome-headless-shell-mac-arm64/chrome-headless-shell'))))
  worker=CodexWorkerClient(workspace,read_roots=[*config['readRoots'],str(playwright),str(browser),"/System/Library/CoreServices/SystemAppearance.bundle","/System/Library/PrivateFrameworks/CoreUI.framework"])
  try:
   await worker.start();await worker.verify_worker_tools()
   result=await worker.request('command/exec',{'command':[config['tools']['node'],str(script)],'cwd':str(workspace),'permissionProfile':PROFILE,'env':{'TMPDIR':str(workspace/'.worker-tmp'),'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD':'1','OPENSSL_CONF':'/dev/null'},'timeoutMs':45000,'outputBytesCap':20000},timeout=55)
   (output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert result['exitCode']==0,result.get('stderr','')
  finally:await worker.close()
asyncio.run(main())
