"""Index exact downloaded wheels; verify pins, Linux dependency closure and notices.

Public PyPI metadata reads only. No package install/import, account or cloud access.
Use a fresh explicit wheel directory and separate fresh evidence directory.
"""
import argparse,datetime,email,hashlib,json,re,sys,urllib.request,zipfile
from pathlib import Path
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name,parse_wheel_filename
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from server.dependency_mirror import inspect_mirror
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--lock',required=True,type=Path);parser.add_argument('--wheels',required=True,type=Path);parser.add_argument('--evidence',required=True,type=Path);parser.add_argument('--python',required=True);parser.add_argument('--machine',choices=['x86_64','aarch64'],default='x86_64');args=parser.parse_args()
assert re.fullmatch(r'3\.13\.\d+',args.python),'This qualification targets the pinned CPython3.13 Linux runtime'
lock=args.lock.read_text();pins={};current=None
for raw in lock.splitlines():
    line=raw.strip().removesuffix('\\').strip()
    if not line:continue
    match=re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)',line)
    if match:
        current=canonicalize_name(match[1]);assert current not in pins,'Duplicate lock record';pins[current]={'version':match[2],'hashes':set()};continue
    match=re.fullmatch(r'--hash=sha256:([0-9a-f]{64})',line);assert current and match,'Use only exact version/hash records';pins[current]['hashes'].add(match[1])
assert 1<=len(pins)<=64 and all(p['hashes']for p in pins.values())
root=args.wheels.resolve();assert root.is_dir()and not(root/'index.json').exists();evidence=args.evidence.resolve();evidence.mkdir(parents=True,exist_ok=False)
artifacts=[];observed={};notices={};metadata_hashes={};selected_hashes={}
for path in sorted(root.iterdir()):
    assert path.is_file()and not path.is_symlink()and path.suffix=='.whl'
    name,version,build,tags=parse_wheel_filename(path.name);name=canonicalize_name(name);assert name in pins and str(version)==pins[name]['version']and name not in observed
    assert any(t.platform=='any'or t.platform.endswith('_'+args.machine)and t.platform.startswith('manylinux')for t in tags),'Select the explicit Linux machine target'
    data=path.read_bytes();digest=hashlib.sha256(data).hexdigest();assert digest in pins[name]['hashes']and len(data)<=32000000
    with zipfile.ZipFile(path)as wheel:
        entries=wheel.infolist();assert len(entries)<=20000 and sum(e.file_size for e in entries)<=256000000
        assert all(not Path(e.filename).is_absolute()and '..'not in Path(e.filename).parts and '\\'not in e.filename and(e.external_attr>>16)&0o170000!=0o120000 for e in entries)
        metadata=[e for e in entries if e.filename.endswith('.dist-info/METADATA')];assert len(metadata)==1 and metadata[0].file_size<=1000000
        raw_metadata=wheel.read(metadata[0]);message=email.message_from_bytes(raw_metadata);assert canonicalize_name(message['Name'])==name and message['Version']==str(version)
        requires_python=message.get('Requires-Python');assert SpecifierSet(requires_python or '').contains(args.python,prereleases=True)
        requirements=message.get_all('Requires-Dist',[]);observed[name]={'version':str(version),'requirements':requirements,'extras':set()}
        licenses=[e for e in entries if re.search(r'(^|/)(LICENSE[^/]*|COPYING[^/]*|NOTICE[^/]*)$',e.filename,re.I)];assert licenses,(name,'No included license notice')
        notices[name]=[]
        for index,item in enumerate(licenses):
            assert item.file_size<=1000000;content=wheel.read(item);notice=evidence/(name+'-'+str(index)+'-'+Path(item.filename).name);notice.write_bytes(content);notices[name].append({'wheelPath':item.filename,'sha256':hashlib.sha256(content).hexdigest()})
        (evidence/(name+'-wheel-metadata.txt')).write_bytes(raw_metadata)
    url='https://pypi.org/pypi/'+name+'/'+str(version)+'/json'
    with urllib.request.urlopen(url,timeout=30)as response:metadata=response.read(2000001)
    assert len(metadata)<=2000000;release=json.loads(metadata);assert canonicalize_name(release['info']['name'])==name and release['info']['version']==str(version)
    candidates=[item for item in release['urls']if item['filename']==path.name and item['digests']['sha256']==digest and not item.get('yanked')];assert len(candidates)==1
    source=candidates[0];assert source['size']==len(data)and source['url'].startswith('https://files.pythonhosted.org/')and '?'not in source['url']
    (evidence/(name+'-pypi.json')).write_bytes(metadata);metadata_hashes[name]=hashlib.sha256(metadata).hexdigest();selected_hashes[name]=digest
    license=message.get('License-Expression')or release['info'].get('license_expression')or release['info'].get('license')or'See preserved upstream notices'
    if len(license)>200:license='See preserved upstream notices'
    artifacts.append({'file':path.name,'name':name,'version':str(version),'kind':'python-wheel','sha256':digest,'bytes':len(data),'license':license,'requiresPython':requires_python,'requiresDist':requirements,'source':{'url':source['url'],'metadataUrl':url,'metadataSha256':metadata_hashes[name],'retrievedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}})
    print('Indexed',name,str(version),len(data),flush=True)
assert set(observed)==set(pins),'Lock and wheel inventory differ'
base={'implementation_name':'cpython','implementation_version':args.python,'platform_python_implementation':'CPython','platform_system':'Linux','sys_platform':'linux','os_name':'posix','platform_machine':args.machine,'python_version':'3.13','python_full_version':args.python}
changed=True
while changed:
    changed=False
    for name,package in observed.items():
        for raw in package['requirements']:
            requirement=Requirement(raw);assert not requirement.url,'No implicit direct dependency URLs'
            assert not requirement.marker or not re.search(r'\bplatform_(?:release|version)\b',str(requirement.marker)),'Kernel-specific markers require explicit target evidence'
            if requirement.marker and not any(requirement.marker.evaluate({**base,'extra':extra})for extra in {'',*package['extras']}):continue
            dependency=canonicalize_name(requirement.name);assert dependency in observed and requirement.specifier.contains(observed[dependency]['version'],prereleases=True),(name,'Unsatisfied target dependency',raw)
            additions=requirement.extras-observed[dependency]['extras']
            if additions:observed[dependency]['extras'].update(additions);changed=True
(root/'index.json').write_text(json.dumps({'format':'atmem.public-dependency-mirror','version':1,'artifacts':artifacts},indent=2)+'\n');checked=inspect_mirror(root)
receipt={'passed':True,'catalogSha256':checked['sha256'],'artifacts':checked['artifacts'],'bytes':checked['bytes'],'lockSha256':hashlib.sha256(args.lock.read_bytes()).hexdigest(),'targetPython':args.python,'targetPlatform':'Linux/'+args.machine+' CPython3.13, pinned manylinux wheel tags','selectedWheelHashes':selected_hashes,'metadataHashes':metadata_hashes,'licenseNotices':notices,'activatedExtras':{name:sorted(p['extras'])for name,p in observed.items()if p['extras']},'packagesInstalled':False,'cloudOperations':False,'boundary':'Exact locked public wheel bytes, PyPI metadata, embedded license notices and target dependency/extra closure. Not runtime/clean image, license legal opinion, publisher signature or vulnerability clearance.'}
(evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'artifacts':checked['artifacts'],'bytes':checked['bytes']}))
