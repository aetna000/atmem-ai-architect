"""Read-only reconciliation of hash-lock declarations and reviewed wheel dependencies."""
import re
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

def dependency_gaps(lock):
    records={canonicalize_name(row['name']):row for row in lock['sources']}
    env={**default_environment(),'python_version':'3.13','python_full_version':'3.13.0','sys_platform':'linux','platform_system':'Linux','platform_machine':'x86_64','implementation_name':'cpython','platform_python_implementation':'CPython'}
    extras={key:{''} for key in records}
    gaps=set();changed=True
    while changed:
        changed=False
        for name,row in records.items():
            for text in row['requiresDist']:
                requirement=Requirement(text)
                if requirement.marker and not any(requirement.marker.evaluate({**env,'extra':extra}) for extra in extras[name]):continue
                target=canonicalize_name(requirement.name)
                if target not in records:gaps.add(name+' requires '+target);continue
                if Version(records[target]['version']) not in requirement.specifier:gaps.add(name+' incompatible '+target)
                new=requirement.extras-extras[target]
                if new:extras[target].update(new);changed=True
    pins={canonicalize_name(name):version for name,version in re.findall(r'^([A-Za-z0-9_.-]+)==([^\s\\]+)',lock['requirements'],re.M)}
    if pins!={key:row['version'] for key,row in records.items()}:gaps.add('lock pins differ from reviewed wheel metadata')
    return gaps

