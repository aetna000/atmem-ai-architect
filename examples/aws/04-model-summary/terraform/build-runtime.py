"""Build deterministic Lambda ZIPs from generated code and hash-locked wheels."""
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
entries=[("block_73756d6d6172792d666e", True, [])]
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
(root/"build"/"artifact-hashes.json").write_text(json.dumps(receipts,indent=2)+"\n")
print(json.dumps({"status":"built","artifacts":receipts}))
