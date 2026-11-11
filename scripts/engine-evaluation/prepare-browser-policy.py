"""Prepare a pinned operator-only Chromium seccomp experiment, never global policy."""
from pathlib import Path
import hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'.local/engine-product/browser-runtime-preparation';out.mkdir(exist_ok=True)
commit='cfe490d941f992655948eee8fd4fd94e1c4234bf';expected='cc3e61cabda6bbc1e53e54d27ba4d55a9d3be829b6dd1a596f4a7b31b1cc7849'
url='https://raw.githubusercontent.com/microsoft/playwright/'+commit+'/utils/docker/seccomp_profile.json'
content=urllib.request.urlopen(url,timeout=30).read();assert hashlib.sha256(content).hexdigest()==expected
policy=json.loads(content);assert policy['defaultAction']=='SCMP_ACT_ERRNO';(out/'seccomp_profile.json').write_bytes(content)
meta={'url':url,'commit':commit,'sha256':expected,'defaultAction':policy['defaultAction'],'scope':'Pinned upstream seccomp plus operator-only Chromium user-namespace probe; no product registration.'}
(out/'seccomp-source.json').write_text(json.dumps(meta,indent=2)+'\n')
policy['syscalls'].append({'names':['chroot'],'action':'SCMP_ACT_ALLOW','args':[]});derived=(json.dumps(policy,indent=2)+'\n').encode();(out/'browser-seccomp.json').write_bytes(derived)
meta.update(upstreamSha256=expected,sha256=hashlib.sha256(derived).hexdigest(),operatorDelta={'allow':['chroot'],'reason':'Browser chroot inside its new user namespace; outer nonroot chroot remains denied and must be tested. No added bounding capabilities or host namespace sharing.'})
(out/'browser-seccomp-source.json').write_text(json.dumps(meta,indent=2)+'\n')
print('Prepared pinned local probe policy:',meta['sha256'])
