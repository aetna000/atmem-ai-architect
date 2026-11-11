#!/usr/bin/env python3
"""Inspect/remount this checkout's operator-owned external artifact storage.

Reads the ignored .local/artifact-storage.json operator profile. No installation,
cloud access, state migration, disk formatting, deletion or unmounting.
"""
import argparse,json,plistlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('action',choices=['status','mount'],nargs='?',default='status')
args=parser.parse_args();profile=ROOT/'.local/artifact-storage.json'
if not profile.is_file():parser.exit(2,'No external artifact profile is configured in this checkout.\n')
data=json.loads(profile.read_text())
if data.get('format')!='atmem.local-artifact-storage' or data.get('version')!=1:parser.error('Unsupported operator storage profile')
external=Path(data['externalRoot'])
if not external.parent.is_mount():parser.exit(2,'External artifact disk is not mounted. Connect MEM0 before using this storage.\n')
volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist',str(external.parent)]))
if volume.get('VolumeUUID')!=data['externalVolumeUuid']:parser.error('The external disk does not match the configured storage volume')
mounts={}
for name,expected in [('providerCache',ROOT/'.local/provider-cache'),('workspaces',ROOT/'.local/external-artifacts')]:
 if name not in data:continue
 entry=data[name];image=Path(entry['image']);target=Path(entry['path'])
 if target!=expected or target.is_symlink():parser.error('The mount must preserve its exact operator-registered directory')
 if not image.is_dir() or not image.resolve().is_relative_to(external.resolve()):parser.error('The sparsebundle is unavailable or outside its operator storage directory')
 if not target.is_mount() and args.action=='mount':
  target.mkdir(parents=True,exist_ok=True)
  if any(target.iterdir()):parser.error('Mount directory contains local files; reconcile them first. No files were overwritten.')
  subprocess.run(['hdiutil','attach','-nobrowse','-mountpoint',str(target),str(image)],check=True)
 images=plistlib.loads(subprocess.check_output(['hdiutil','info','-plist'])).get('images',[])
 owned=any(Path(item.get('image-path','/')).resolve()==image.resolve() and any(entity.get('mount-point')==str(target) for entity in item.get('system-entities',[])) for item in images)
 if not target.is_mount() or not owned:parser.exit(2,'A configured artifact volume is not mounted. Run this command with mount.\n')
 mounts[name]=str(target)
print(json.dumps({'status':'available','externalRoot':str(external),'mounts':mounts,'registeredProviderPathPreserved':True,'initialLogicalBytesOffloaded':data['logicalBytesOffloaded']},indent=2))
