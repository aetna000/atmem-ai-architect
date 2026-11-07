import lock from './runtime/aws-python-lock.json' with {type:'json'};
// All filenames are compiler-generated hex addresses, never executable model content.
export function pythonRuntimeFiles(entries) {
 if(!entries.length)return {};
 const pythonEntries=entries.map(e=>`(${JSON.stringify(e.address)}, ${e.sdk?'True':'False'}, ${JSON.stringify(e.modules||[])})`).join(',');
 return {
  ...(entries.some(e=>e.sdk)?{'runtime-requirements.lock':lock.requirements,'runtime-dependency-sources.json':JSON.stringify(lock.sources,null,2)}:{}),
  'build-runtime.py':`"""Build deterministic Lambda ZIPs from generated code and hash-locked wheels."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

root=Path(__file__).resolve().parent
entries=[${pythonEntries}]
receipts=[]
for address, sdk, modules in entries:
    if not re.fullmatch(r"block_[0-9a-f]+", address):
        raise ValueError("Invalid generated component address")
    folder=root/"build"/address
    if folder.exists():shutil.rmtree(folder)
    folder.mkdir(parents=True)
    if sdk:
        subprocess.run([sys.executable,"-I","-m","pip","--isolated","install","--disable-pip-version-check","--no-compile","--only-binary=:all:","--require-hashes","--python-version","3.13","--implementation","cp","--abi","cp313","--platform","manylinux2014_aarch64","--index-url","https://pypi.org/simple","--target",str(folder),"-r",str(root/"runtime-requirements.lock")],check=True)
    shutil.copyfile(root/"handlers"/(address+".py"),folder/(address+".py"))
    for module in modules:
        if not re.fullmatch(r"[a-z_]+[.]py",module):raise ValueError("Invalid generated module name")
        shutil.copyfile(root/"handlers"/address/module,folder/module)
    archive=root/"build"/(address+".zip")
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
        for file in sorted(folder.rglob("*")):
            if not file.is_file() or "__pycache__" in file.parts or "bin" in file.relative_to(folder).parts:continue
            if file.name == "RECORD" and file.parent.name.endswith(".dist-info"):continue
            item=zipfile.ZipInfo(file.relative_to(folder).as_posix(),date_time=(1980,1,1,0,0,0))
            item.create_system=3
            item.external_attr=0o100644 << 16
            item.compress_type=zipfile.ZIP_DEFLATED
            output.writestr(item,file.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    receipts.append({"component":address,"sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"sdkPinned":sdk})
(root/"build"/"artifact-hashes.json").write_text(json.dumps(receipts,indent=2)+"\\n")
print(json.dumps({"status":"built","artifacts":receipts}))
`,
  'BUILD.md':'# Build application artifacts\n\nRun `python3 build-runtime.py` before Terraform validation or planning, then `python3 -m unittest discover -s app-tests -p "*_test.py"`. Python 3.13 is the deployment runtime. The builder uses fixed ZIP metadata and sorted entries so identical inputs produce identical artifact hashes. SDK workloads install the complete pinned dependency set using wheel hashes, targeting Python 3.13 on Linux ARM64. No source distributions or install hooks are allowed. Record build/artifact-hashes.json with the reviewed plan.\n\nReview dependency updates deliberately and rerun acceptance tests. Keep build/, ZIPs, state, backend configuration and deployment variable files out of source control; commit generated source and reviewed provider lock files. No AWS calls occur during this build.\n',
 };
}
