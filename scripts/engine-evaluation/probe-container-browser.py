"""Independent operator probe, not a registered product validator or acceptance gate."""
import hashlib,io,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.local_validation import DockerValidationWorker,ValidationSpec
out=ROOT/'.local/engine-product/browser-runtime-preparation'
image=json.loads((out/'derived-image.json').read_text())['imageId']
script='''import {chromium} from '/opt/atmem/playwright-core/index.mjs';
const browser=await chromium.launch({headless:true,chromiumSandbox:true});
try{
 const page=await browser.newPage();
 await page.route('**/*',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><button id="go">Ready</button>'}));
 await page.goto('https://local-test.invalid/');
 if(await page.locator('#go').textContent()!=='Ready')throw Error('Browser did not execute');
 console.log('CONTAINER_BROWSER_EXECUTED');
}finally{await browser.close();}
'''
data=io.BytesIO()
with zipfile.ZipFile(data,'w') as z:z.writestr('probe.mjs',script)
content=data.getvalue();worker=DockerValidationWorker('unix://'+str(Path.home()/'.colima/architect-qualification/docker.sock'))
result=worker.run(content,hashlib.sha256(content).hexdigest(),ValidationSpec('browser-policy-probe',image,('/usr/bin/node','probe.mjs'),platform='linux/arm64',bootstrap_python='/usr/bin/python3'))
(out/'browser-probe.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['output']);assert result['status']=='passed'
