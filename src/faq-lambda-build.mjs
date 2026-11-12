export function faqLambdaBuild(addresses){
 if(!addresses.length||addresses.some(n=>!/^block_[0-9a-f]+$/.test(n)))throw Error('Invalid owned Lambda application addresses');
 return {'build-runtime.py':`"""Build deterministic Python 3.13 / Linux x86_64 public FAQ ZIPs."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
root=Path(__file__).resolve().parent
receipts=[]
for address in ${JSON.stringify(addresses)}:
    source=root/'applications'/address;folder=root/'build'/address
    if folder.exists():shutil.rmtree(folder)
    folder.mkdir(parents=True)
    subprocess.run([sys.executable,'-I','-m','pip','--isolated','install','--disable-pip-version-check','--no-compile','--only-binary=:all:','--require-hashes','--python-version','3.13','--implementation','cp','--abi','cp313','--abi','abi3','--platform','manylinux_2_34_x86_64','--platform','manylinux_2_28_x86_64','--platform','manylinux2014_x86_64','--index-url','https://pypi.org/simple','--target',str(folder),'-r',str(source/'requirements.lock')],check=True)
    modules=['public_faq.py','public_catalog_store.py','public_faq_app.py','structured_http.py','structured_output.py','aws_json_model.py','lambda_faq.py']
    for name in modules+['output-contract.json','faq-deployment.json']:
        shutil.copyfile(source/name,folder/name)
    shutil.copytree(source/'web',folder/'web')
    archive=root/'build'/(address+'.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as output:
        for file in sorted(folder.rglob('*')):
            if not file.is_file() or '__pycache__' in file.parts or 'bin' in file.relative_to(folder).parts:continue
            item=zipfile.ZipInfo(file.relative_to(folder).as_posix(),date_time=(1980,1,1,0,0,0));item.create_system=3;item.external_attr=0o100644<<16;item.compress_type=zipfile.ZIP_DEFLATED
            output.writestr(item,file.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    if archive.stat().st_size>50*1024*1024:raise ValueError('ZIP exceeds direct Lambda upload boundary; implement an artifact-store publication contract rather than silently changing deployment')
    receipts.append({'component':address,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'target':'python3.13-linux-x86_64','sourceFiles':{str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()}})
(root/'build'/'artifact-hashes.json').write_text(json.dumps(receipts,indent=2)+'\\n')
print(json.dumps({'status':'built','artifacts':receipts}))
`};
}
