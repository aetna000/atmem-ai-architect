"""Resolve primary vendor runtime tags once; build only immutable verified digests."""
import hashlib,json,re,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ACCEPT=', '.join(['application/vnd.oci.image.index.v1+json','application/vnd.docker.distribution.manifest.list.v2+json','application/vnd.oci.image.manifest.v1+json','application/vnd.docker.distribution.manifest.v2+json'])
def get(url,headers=None):
 request=urllib.request.Request(url,headers={'User-Agent':'AtMem-Architect-runtime-qualification',**(headers or {})})
 with urllib.request.urlopen(request,timeout=40) as response:return response.read(),dict(response.headers.items())
def docker(repository,tag):
 token=json.loads(get('https://auth.docker.io/token?'+urllib.parse.urlencode({'service':'registry.docker.io','scope':'repository:'+repository+':pull'}))[0])['token']
 raw,headers=get('https://registry-1.docker.io/v2/'+repository+'/manifests/'+tag,{'Authorization':'Bearer '+token,'Accept':ACCEPT})
 digest='sha256:'+hashlib.sha256(raw).hexdigest()
 if {key.lower():value for key,value in headers.items()}.get('docker-content-digest')!=digest:raise RuntimeError('Vendor manifest failed integrity verification')
 return {'tag':repository+':'+tag,'image':repository+'@'+digest,'registry':'Docker Hub vendor namespace'}
release=json.loads(get('https://api.github.com/repos/hashicorp/terraform/releases/latest')[0])
if release.get('prerelease') or not re.fullmatch(r'v1\.\d+\.\d+',release['tag_name']):raise RuntimeError('Review the current stable Terraform 1.x release')
raw,headers=get('https://mcr.microsoft.com/v2/playwright/manifests/v1.64.1-noble',{'Accept':ACCEPT})
mcr='sha256:'+hashlib.sha256(raw).hexdigest()
if {key.lower():value for key,value in headers.items()}.get('docker-content-digest')!=mcr:raise RuntimeError('Playwright vendor manifest failed integrity verification')
uv_token=json.loads(get('https://ghcr.io/token?'+urllib.parse.urlencode({'service':'ghcr.io','scope':'repository:astral-sh/uv:pull'}))[0])['token']
raw,headers=get('https://ghcr.io/v2/astral-sh/uv/manifests/latest',{'Authorization':'Bearer '+uv_token,'Accept':ACCEPT});uv='sha256:'+hashlib.sha256(raw).hexdigest()
if {key.lower():value for key,value in headers.items()}.get('docker-content-digest')!=uv:raise RuntimeError('uv vendor manifest failed integrity verification')
data={'resolvedAt':datetime.now(timezone.utc).isoformat(),'platform':'linux/amd64','pythonVersion':'3.13.12',
      'playwright':{'image':'mcr.microsoft.com/playwright@'+mcr,'tag':'mcr.microsoft.com/playwright:v1.64.1-noble','source':'https://playwright.dev/docs/docker'},
      'uv':{'image':'ghcr.io/astral-sh/uv@'+uv,'source':'https://docs.astral.sh/uv/guides/integration/docker/'},
      'node':docker('library/node','26-bookworm-slim'),'docker':docker('library/docker','29-cli'),
      'terraform':{**docker('hashicorp/terraform',release['tag_name'][1:]),'version':release['tag_name'][1:],'releaseSource':release['html_url']}}
Path('hosted/deploy/runtime-images.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({key:row['image'] for key,row in data.items() if isinstance(row,dict)},indent=2))
