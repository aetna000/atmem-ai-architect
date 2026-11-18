"""Build small deterministic extension/schema archives without publishing."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def archive(target,entries):
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for label,path in sorted(entries):
            if path.is_symlink() or not path.is_file():raise ValueError('Distribution requires regular explicit files')
            info=zipfile.ZipInfo(label,date_time=(2020,1,1,0,0,0));info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,path.read_bytes())
    return {'file':target.name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    if output.is_relative_to(ROOT):raise ValueError('Use an artifact output directory')
    names=['extension.yml','config-template.yml','README.md','LICENSE','THIRD_PARTY_NOTICES.md','commands/speckit.atmem.review.md','examples/architecture.md']
    entries=[(name,ROOT/'spec-kit'/name) for name in names]
    entries.append(('CHANGELOG.md',ROOT/'CHANGELOG.md'))
    reports=[archive(output/'spec-kit-atmem-0.1.0.zip',entries)]
    names=['README.md','LICENSE','THIRD_PARTY_NOTICES.md','command/atmem-review.md','command/INSTALL.md','schemas/atmem-reviewed/schema.yaml','examples/architecture.md']
    names += ['schemas/atmem-reviewed/templates/'+name+'.md' for name in ['proposal','spec','design','tasks','review']]
    entries=[(name,ROOT/'openspec'/name) for name in names]
    entries.append(('CHANGELOG.md',ROOT/'CHANGELOG.md'))
    reports.append(archive(output/'openspec-atmem-reviewed-0.1.0.zip',entries))
    print(json.dumps({'status':'built_unpublished','artifacts':reports},indent=2))


if __name__=='__main__':main()
