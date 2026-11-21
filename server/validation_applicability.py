"""Operator-reviewed file applicability, never a semantic coverage claim.

Rules select checks for an immutable manifest. They cannot supply commands, infer
cloud targets or declare requirements satisfied. Missing registration is explicit.
"""
from dataclasses import dataclass
from fnmatch import fnmatchcase
import re


def _pattern(value):
    if not isinstance(value,str) or not value or len(value)>240 or any(ord(c)<32 for c in value) or '\\' in value:
        raise ValueError('Applicability patterns require bounded relative POSIX paths')
    parts=value.split('/')
    if len(parts)>24 or any(part in {'','..','.'} or ('**' in part and part!='**') for part in parts):
        raise ValueError('Use relative path segments and whole-segment ** only')
    return value


def matches(pattern, name):
    """Whole-path glob; * stays within a segment, ** spans zero or more segments."""
    segments=pattern.split('/');parts=name.split('/')
    reachable={0}
    for segment in segments:
        if segment=='**':
            reachable=set(range(min(reachable),len(parts)+1)) if reachable else set()
        else:
            reachable={index+1 for index in reachable if index<len(parts) and fnmatchcase(parts[index],segment)}
    return len(parts) in reachable


@dataclass(frozen=True)
class FileDigest:
    pattern: str
    sha256: str

    def __post_init__(self):
        _pattern(self.pattern)
        if not isinstance(self.sha256,str) or not re.fullmatch(r'[a-f0-9]{64}',self.sha256):raise ValueError('Use a complete lowercase SHA256 file pin')

    @classmethod
    def parse(cls,value):
        if not isinstance(value,dict)or set(value)!={'pattern','sha256'}:raise ValueError('File digest applicability requires exactly pattern and sha256')
        return cls(value['pattern'],value['sha256'])

    def public(self):return {'pattern':self.pattern,'sha256':self.sha256}


@dataclass(frozen=True)
class FileApplicability:
    any_of: tuple[str,...]
    all_of: tuple[str,...] = ()
    none_of: tuple[str,...] = ()
    any_file_sha256: tuple[FileDigest,...] = ()

    def __post_init__(self):
        if not self.any_of:raise ValueError('An automatic check needs explicit positive file applicability')
        for patterns in (self.any_of,self.all_of,self.none_of):
            if not isinstance(patterns,tuple) or len(patterns)>16 or any(not isinstance(pattern,str) for pattern in patterns) or len(set(patterns))!=len(patterns):
                raise ValueError('Use at most sixteen unique patterns per applicability group')
            for pattern in patterns:_pattern(pattern)
        if not isinstance(self.any_file_sha256,tuple)or len(self.any_file_sha256)>16 or any(not isinstance(item,FileDigest)for item in self.any_file_sha256)or len(set(self.any_file_sha256))!=len(self.any_file_sha256):raise ValueError('Use at most sixteen unique reviewed file digest alternatives')

    @classmethod
    def parse(cls, value):
        if not isinstance(value,dict) or set(value)-{'anyOf','allOf','noneOf','anyFileSha256'} or any(not isinstance(group,list) for group in value.values()):
            raise ValueError('Register explicit file patterns and optional reviewed digest alternatives')
        return cls(tuple(value.get('anyOf',[])),tuple(value.get('allOf',[])),tuple(value.get('noneOf',[])),tuple(FileDigest.parse(item)for item in value.get('anyFileSha256',[])))

    def public(self):
        result={'anyOf':self.any_of,'allOf':self.all_of,'noneOf':self.none_of}
        if self.any_file_sha256:result['anyFileSha256']=[item.public()for item in self.any_file_sha256]
        return result

    def assess(self, files):
        regular=tuple(file for file in files if file.get('kind')=='file')
        names=tuple(file['path']for file in regular)
        def found(pattern):return any(matches(pattern,name) for name in names)
        positive=[pattern for pattern in self.any_of if found(pattern)]
        missing=[pattern for pattern in self.all_of if not found(pattern)]
        excluded=[pattern for pattern in self.none_of if found(pattern)]
        pinned=[{'path':file['path'],**rule.public()}for rule in self.any_file_sha256 for file in regular if file.get('sha256')==rule.sha256 and matches(rule.pattern,file['path'])]
        return {'applies':bool(positive) and not missing and not excluded and (bool(pinned)or not self.any_file_sha256),
                **({'matchedAnyFileSha256':pinned,'requiredAnyFileSha256':[rule.public()for rule in self.any_file_sha256]}if self.any_file_sha256 else {}),
                'matchedAnyOf':positive,'missingAllOf':missing,'matchedNoneOf':excluded}
