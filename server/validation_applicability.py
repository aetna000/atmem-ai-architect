"""Operator-reviewed file applicability, never a semantic coverage claim.

Rules select checks for an immutable manifest. They cannot supply commands, infer
cloud targets or declare requirements satisfied. Missing registration is explicit.
"""
from dataclasses import asdict, dataclass
from fnmatch import fnmatchcase


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
class FileApplicability:
    any_of: tuple[str,...]
    all_of: tuple[str,...] = ()
    none_of: tuple[str,...] = ()

    def __post_init__(self):
        if not self.any_of:raise ValueError('An automatic check needs explicit positive file applicability')
        for patterns in (self.any_of,self.all_of,self.none_of):
            if not isinstance(patterns,tuple) or len(patterns)>16 or any(not isinstance(pattern,str) for pattern in patterns) or len(set(patterns))!=len(patterns):
                raise ValueError('Use at most sixteen unique patterns per applicability group')
            for pattern in patterns:_pattern(pattern)

    @classmethod
    def parse(cls, value):
        if not isinstance(value,dict) or set(value)-{'anyOf','allOf','noneOf'} or any(not isinstance(group,list) for group in value.values()):
            raise ValueError('Register explicit anyOf/allOf/noneOf file patterns')
        return cls(tuple(value.get('anyOf',[])),tuple(value.get('allOf',[])),tuple(value.get('noneOf',[])))

    def public(self):
        return dict(zip(('anyOf','allOf','noneOf'),asdict(self).values()))

    def assess(self, files):
        names=tuple(file['path'] for file in files if file.get('kind')=='file')
        def found(pattern):return any(matches(pattern,name) for name in names)
        positive=[pattern for pattern in self.any_of if found(pattern)]
        missing=[pattern for pattern in self.all_of if not found(pattern)]
        excluded=[pattern for pattern in self.none_of if found(pattern)]
        return {'applies':bool(positive) and not missing and not excluded,
                'matchedAnyOf':positive,'missingAllOf':missing,'matchedNoneOf':excluded}
