"""Explicit operator preparation of pinned public pure-Python wheels.

Downloads only exact requested releases from PyPI metadata/hashed pythonhosted
wheels. No package install/import, global settings, account or model execution.
"""
import argparse,datetime,hashlib,io,json,re,sys,urllib.request,zipfile
from pathlib import Path
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from server.dependency_mirror import inspect_mirror
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--package',action='append',required=True,help='Exact name==version, no URLs/extras');parser.add_argument('--target-python',action='append',required=True);parser.add_argument('--target-platform',action='append',choices=['linux/amd64','linux/arm64'],required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
pins={}
for value in args.package:
 if not re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+',value):parser.error('Use explicit exact package releases')
 name,version=value.split('==');name=canonicalize_name(name)
 if name in pins:parser.error('Duplicate package pin')
 pins[name]=version
if any(not re.fullmatch(r'3\.\d+(?:\.\d+)?',version) for version in args.target_python):parser.error('Name each actual target Python version')
root=args.output.resolve();evidence=args.evidence.resolve();root.mkdir(parents=True,exist_ok=False);evidence.mkdir(parents=True,exist_ok=False)
artifacts=[]
for name,version in pins.items():
 url='https://pypi.org/pypi/'+name+'/'+version+'/json'
 with urllib.request.urlopen(url,timeout=20)as response:
  metadata=response.read(2000001);assert len(metadata)<=2000000
 data=json.loads(metadata);assert canonicalize_name(data['info']['name'])==name and data['info']['version']==version
 python=data['info'].get('requires_python') or None
 assert all(SpecifierSet(python or '').contains(target,prereleases=True) for target in args.target_python),(name,'Unsupported Python version')
 requirements=data['info'].get('requires_dist') or []
 for target in args.target_python:
  for raw in requirements:
   requirement=Requirement(raw)
   if requirement.marker:
    # Never resolve target-platform dependencies using the operator host's OS.
    # Kernel-specific markers need an explicit richer qualification contract.
    assert not re.search(r'\bplatform_(?:release|version)\b',str(requirement.marker)),(name,'Unsupported kernel-specific dependency marker',raw)
    environments=[{'extra':'','implementation_name':'cpython','implementation_version':target,'platform_python_implementation':'CPython','platform_system':'Linux','sys_platform':'linux','os_name':'posix','platform_machine':'aarch64' if platform=='linux/arm64' else 'x86_64','python_version':'.'.join(target.split('.')[:2]),'python_full_version':target if len(target.split('.'))==3 else target+'.0'}for platform in args.target_platform]
    if not any(requirement.marker.evaluate(environment)for environment in environments):continue
   dependency=canonicalize_name(requirement.name)
   assert dependency in pins and requirement.specifier.contains(pins[dependency],prereleases=True),(name,'Unsatisfied explicit dependency closure',raw)
 choices=[entry for entry in data['urls']if entry['filename'].endswith('none-any.whl') and not entry.get('yanked')]
 assert len(choices)==1,(name,'Choose exactly one unyanked pure-Python wheel')
 selected=choices[0];download=selected['url'];assert download.startswith('https://files.pythonhosted.org/') and '?' not in download
 with urllib.request.urlopen(download,timeout=30)as response:content=response.read(32000001)
 assert len(content)==selected['size']<=32000000 and hashlib.sha256(content).hexdigest()==selected['digests']['sha256']
 with zipfile.ZipFile(io.BytesIO(content))as wheel:
  assert len(wheel.infolist())<=20000 and sum(item.file_size for item in wheel.infolist())<=256000000
  assert all(not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts and '\\' not in item.filename for item in wheel.infolist())
  licenses=[item.filename for item in wheel.infolist()if re.search(r'(^|/)(LICENSE[^/]*|COPYING[^/]*|NOTICE[^/]*)$',item.filename,re.I)]
  assert licenses,(name,'No redistributable license notice found')
  for file in licenses:
   assert wheel.getinfo(file).file_size<=1000000
   target=evidence/(name+'-'+Path(file).name);target.write_bytes(wheel.read(file))
 (root/selected['filename']).write_bytes(content);(evidence/(name+'-metadata.json')).write_bytes(metadata)
 license=data['info'].get('license_expression') or data['info'].get('license') or 'See included upstream notices; license review required'
 if len(license)>200:license='See included upstream license notices'
 artifacts.append({'file':selected['filename'],'name':name,'version':version,'kind':'python-wheel','sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content),'license':license,'requiresPython':python,'requiresDist':requirements,'source':{'url':download,'metadataUrl':url,'metadataSha256':hashlib.sha256(metadata).hexdigest(),'retrievedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}})
 print('Prepared',name,version,len(content),flush=True)
(root/'index.json').write_text(json.dumps({'format':'atmem.public-dependency-mirror','version':1,'artifacts':artifacts},indent=2)+'\n')
checked=inspect_mirror(root);(evidence/'receipt.json').write_text(json.dumps({'passed':True,'catalogSha256':checked['sha256'],'artifacts':checked['artifacts'],'bytes':checked['bytes'],'targetPythonVersions':args.target_python,'targetPlatforms':args.target_platform,'packagePins':pins,'cloudOperations':False,'packagesInstalled':False,'scope':'Exact public PyPI releases and HTTPS registry digests; explicit CPython/Linux base dependency closure/target-version metadata and license notices preserved. No code import, application build or runtime compatibility proof; no claim of publisher-signature verification or vulnerability clearance.'},indent=2)+'\n')
