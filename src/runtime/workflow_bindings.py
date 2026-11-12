"""Pure deferred public-output binding. No cloud lookup or approval inference."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
if __package__:
    from .workflow_profile import ApplicationProfile,IDENTITY_KEYS
    from .workflow_payload import encoded
else:
    from workflow_profile import ApplicationProfile,IDENTITY_KEYS
    from workflow_payload import encoded

ENVIRONMENTS={'staging','production','qualification'}
PROVIDERS={'aws','azure','gcp','ibm','tools'}


def reference(value):
    if type(value)is not dict or set(value)!={'nativeOutput'}:raise ValueError('Use an explicit public native-output reference')
    ref=value['nativeOutput']
    if type(ref)is not dict or set(ref)!={'componentId','provider','environment','name'}:raise ValueError('Use an exact native-output owner')
    if type(ref['componentId'])is not str or not 1<=len(ref['componentId'].encode())<=512 or any(ord(c)<32 for c in ref['componentId']):raise ValueError('Use the complete output component identity')
    if type(ref['provider'])is not str or ref['provider']not in PROVIDERS or type(ref['environment'])is not str or ref['environment']not in ENVIRONMENTS:raise ValueError('Use the exact output provider/environment')
    if type(ref['name'])is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,79}',ref['name'])or re.search(r'secret|password|credential|private_?key',ref['name'],re.I):raise ValueError('Only reviewed public output names may bind')
    return ref


@dataclass(frozen=True,init=False)
class ApplicationTemplate:
    _encoded:bytes

    def __init__(self,value):
        raw=encoded(value);data=json.loads(raw)
        if type(data)is not dict or data.get('format')!='approval-application-template-v1':raise ValueError('Use a versioned application template')
        trial=json.loads(raw);trial['format']='approval-application-v1';refs=[]
        if type(trial.get('publicOrigin'))is dict:
            refs.append(('publicOrigin',reference(trial['publicOrigin'])));trial['publicOrigin']='https://unresolved.invalid'
        identity=trial.get('identitySettings')
        if type(identity)is dict:
            for key,val in identity.items():
                if type(val)is dict:refs.append(('identitySettings/'+key,reference(val)));identity[key]='UNRESOLVED_NATIVE_OUTPUT'
        dest=trial.get('destinationContract')
        if type(dest)is dict:
            for key in ['endpointSha256','scope']:
                if type(dest.get(key))is dict:
                    refs.append(('destinationContract/'+key,reference(dest[key])));dest[key]='0'*64 if key=='endpointSha256'else'unresolved'
        ApplicationProfile(trial)
        if not refs:raise ValueError('A deferred template must retain at least one output reference')
        for path,ref in refs:
            if ref['environment']!=data['environment']:raise ValueError('Output environment differs from the application template')
            if path.startswith('identitySettings/')and ref['provider']!=data['provider']:raise ValueError('Native identity output provider differs from the selected adapter')
        object.__setattr__(self,'_encoded',raw)

    @property
    def data(self):return json.loads(self._encoded)
    @property
    def sha256(self):return hashlib.sha256(self._encoded).hexdigest()
    @property
    def references(self):
        data=self.data;result=[]
        for key in ['publicOrigin']:
            if type(data[key])is dict:result.append({'path':key,**reference(data[key])})
        for section in ['identitySettings','destinationContract']:
            for key,value in data[section].items():
                if type(value)is dict:result.append({'path':section+'/'+key,**reference(value)})
        return result


def application_declaration(value):
    return ApplicationTemplate(value)if type(value)is dict and value.get('format')=='approval-application-template-v1'else ApplicationProfile(value)


def resolve_template(template,ledger):
    if type(template)is not ApplicationTemplate:raise ValueError('Use an immutable owned template')
    raw=encoded(ledger);ledger=json.loads(raw)
    if type(ledger)is not dict or set(ledger)!={'version','outputs'}or type(ledger['version'])is not int or ledger['version']!=1 or type(ledger['outputs'])is not list or not 1<=len(ledger['outputs'])<=128:raise ValueError('Use a bounded public-output ledger')
    by_key={};snapshots={}
    for item in ledger['outputs']:
        if type(item)is not dict or set(item)!={'componentId','provider','environment','name','value','sensitive','sourceSha256'}:raise ValueError('Use exact public output records')
        reference({'nativeOutput':{key:item[key]for key in ['componentId','provider','environment','name']}})
        if item['sensitive']is not False or type(item['value'])is not str or not 1<=len(item['value'].encode())<=2000:raise ValueError('Sensitive or unbounded values cannot enter application profiles')
        if re.search(r'-----BEGIN .*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-(?:ant-)?[A-Za-z0-9_-]{20,}',item['value']):raise ValueError('Credential-like output refused')
        if type(item['sourceSha256'])is not str or not re.fullmatch(r'[0-9a-f]{64}',item['sourceSha256']):raise ValueError('Retain the source artifact identity')
        owner=tuple(item[key]for key in ['componentId','provider','environment']);key=owner+(item['name'],)
        if key in by_key:raise ValueError('Duplicate output identity; no version was chosen')
        if owner in snapshots and snapshots[owner]!=item['sourceSha256']:raise ValueError('One component cannot mix output snapshots')
        snapshots[owner]=item['sourceSha256'];by_key[key]=item
    data=template.data;data['format']='approval-application-v1';used={}
    for ref in template.references:
        key=tuple(ref[k]for k in ['componentId','provider','environment','name']);item=by_key.get(key)
        if item is None:raise ValueError('A required native output is unresolved; no default was substituted')
        keys=ref['path'].split('/');target=data
        for part in keys[:-1]:target=target[part]
        target[keys[-1]]=item['value'];used[key]=item
    profile=ApplicationProfile(data)
    receipt={'format':'atmem.application-binding','version':1,'templateSha256':template.sha256,'profileSha256':profile.sha256,'inputs':{'version':1,'outputs':[used[key]for key in sorted(used)]},'status':'structurally_resolved','cloudVerified':False}
    return profile,receipt


def read_json(path):
    with Path(path).open('rb')as stream:raw=stream.read(64001)
    if len(raw)>64000:raise ValueError('Binding artifact exceeds its byte boundary')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate binding artifact field')
            result[key]=value
        return result
    return json.loads(raw.decode(),object_pairs_hook=unique)


def load_bound_profile(template_path,directory):
    template=ApplicationTemplate(read_json(template_path));directory=Path(directory)
    receipt=read_json(directory/'binding-receipt.json')
    if type(receipt)is not dict or set(receipt)!={'format','version','templateSha256','profileSha256','inputs','status','cloudVerified'}:raise ValueError('Missing or invalid binding receipt; resolve public outputs before starting')
    profile,expected=resolve_template(template,receipt['inputs'])
    if encoded(receipt)!=encoded(expected) or ApplicationProfile(read_json(directory/'application-profile.json')).data!=profile.data:raise ValueError('Binding/profile bytes differ from the owned template and inputs')
    return profile


def write_binding(template_path,ledger_path,directory):
    profile,receipt=resolve_template(ApplicationTemplate(read_json(template_path)),read_json(ledger_path))
    profile_bytes,receipt_bytes=encoded(profile.data),encoded(receipt)
    directory=Path(directory);directory.mkdir(mode=0o700,parents=False,exist_ok=False)
    # Receipt is the commit marker. Readers reject an interrupted/partial bundle.
    with(directory/'application-profile.json').open('xb')as stream:stream.write(profile_bytes)
    with(directory/'binding-receipt.json').open('xb')as stream:stream.write(receipt_bytes)
    return receipt
