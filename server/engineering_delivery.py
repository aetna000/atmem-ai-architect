"""Backend-owned public handoff contract, independent of business/provider recipes."""
import hashlib
from pathlib import Path

CONTRACT='''# AtMem implementation delivery contract

This file and atmem-tools/prepare.py are backend-supplied inputs. Preserve them.
Client requirements, provider choices, ownership and accepted decisions remain authoritative.

## Worker environment and exported project

The worker supplies .tools and .worker-tmp for local engineering. Those directories,
.git, .terraform and Python caches are NOT included in the downloaded handoff.
Do not require unexported files, private host paths or hidden worker state to run the
delivered project. Keep all implementation, tests, configuration, schemas and runbooks
in the public project files. Runtime dependency and platform requirements must be
explicit; a tool available to this worker does not establish target compatibility.

Prefer ordinary portable build/test commands. If project scripts use .tools aliases,
document setup from a fresh unpack before those scripts. The included offline helper
accepts existing operator-selected tools; it never installs packages or configures
cloud credentials. Example (adjust required tools and target runtime to this project):

    python3 atmem-tools/prepare.py --require python

For Terraform/Node projects the operator also supplies the installed executable paths
and an approved offline provider mirror with --node, --terraform, --provider-mirror
and the corresponding --require options. Document pinned dependency versions, supported
platforms, checksum/provenance limits and the actual commands. Do not assume the helper
vendors Python, Node, Terraform, providers or the application SDK. Missing dependencies
remain explicit, not skipped passes. Preserve worker tool registrations while generating;
the helper is for preparing the exported copy in a receiving engineer's environment.

The helper creates project-local OpenSSL/CLI configuration. Project scripts may supply
their own documented local setup. No account plan, apply, migration or deployment is
authorized by this contract. Keep deployment ZIPs/images limited to actual runtime
files; do not ship tool registrations, client snapshots or synthetic test transports
as application behavior.

## Completion evidence

Run the real emitted checks and label schema, provider mocks, local runtime and
unexecuted checks separately. Include clean-unpack/build/test instructions and an
artifact manifest. Do not infer whole-system correctness from generated tests.
Preserve unsupported requirements and unknowns. Population/usage estimates are sizing
facts, not automatically customer authorization quotas or accepted company policy;
separate proposed operational guards from explicit client requirements.
'''


def seed_delivery(workspace):
    root=Path(workspace)
    files={'ATMEM_DELIVERY.md':CONTRACT.encode(),
           'atmem-tools/prepare.py':(Path(__file__).parent/'engineering_assets/prepare_tools.py').read_bytes()}
    for name,content in files.items():
        target=root/name
        for parent in target.parents:
            if parent==root:break
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise ValueError('Backend delivery inputs require project-owned directories')
        if target.exists() or target.is_symlink():raise ValueError('Backend delivery inputs cannot overwrite project content')
    for name,content in files.items():
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    return {name:hashlib.sha256(content).hexdigest() for name,content in files.items()}
