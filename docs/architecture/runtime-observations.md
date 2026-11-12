# Operator runtime observations

The validator catalogue can include operator-pinned, empty-source observations.
These describe an actual immutable image/profile execution, not application,
requirement, cloud/account or deployment acceptance. They never authorize additional
permissions. `available` describes worker/profile availability, not support for every
SDK operation or process safeguard.

`observe-runtime.py` emits legacy version1 package/executable metadata by default.
Existing version1 registrations and public contract shapes remain unchanged.

Opt in with `--process-controls` (Python only) to emit version2. It additionally
observes Linux `PR_SET_NO_NEW_PRIVS` and installation of a one-instruction
`SECCOMP_RET_ALLOW` filter using typed libc `prctl`. This filter stacks with the
existing outer policy; it cannot loosen it. No client code, cloud request, package
installation or image pull occurs. The PostgreSQL profile may start its usual
isolated local database to observe its actual server version.

The receipt binds the exact probe fragment hash, complete raw output, runtime,
worker policy/identity, date and execution-context digest. Context includes process
machine, kernel release, a SHA256 of the kernel boot UUID, and UID. It omits the raw
boot identifier. `supported:false` records an attempted syscall failure and errno;
`null` means unobserved (for example, the prerequisite failed), never unsupported.

Example (operator paths and an already reviewed registration are required):

```sh
.venv/bin/python scripts/engine-evaluation/observe-runtime.py \
  --validators /absolute/operator/validators.json \
  --validator python-tests --kind python --process-controls \
  --endpoint unix:///absolute/operator/docker.sock \
  --output /absolute/operator/runtime-observation.json
```

The output file must not already exist; failed receipts remain available for review.
Pin the resulting bytes by absolute `runtimeReceipt.path` and SHA256 in the operator
validator registration. The server rejects malformed/inconsistent syscall outcomes,
unknown context fields, changed output/context hashes and an unrecognized probe.
Registered observations appear in `runtimeEvidence` in the existing catalogue.
Different observations change the validator contract and historical evidence binding.

This is a **last-observed snapshot**, not an image-only property, current live-health
check or a freshness lease. Worker identity currently hashes the endpoint; that is
not a kernel identity. Reobserve and register new pinned evidence after worker,
kernel, boot or policy changes. Do not select a required process safeguard merely
from image architecture or a cached observation. Negative observations should inform
implementation/runtime choice; they do not permit removal of required protections,
changing the requested platform, or promotion of unexecuted tests into passes.

Linux AMD64 userspace running on an ARM64 VM is not native AMD64 kernel evidence.
Qualify a suitable execution context and then independently check the unchanged
application against all of its original requirements.
