# Native Google per-file document job prototype — local qualification

Implemented the owned Batch controller, native GCS byte transport and trusted
sequential download/upload CLIs. The parser has explicit local mounts, UID10001,
read-only root/input, bounded tmpfs/resources, native network blocking and no
streaming/log/identity fallback. Native source/company/job guards surround remote
operations. Lost create acknowledgements, failures, wrong results, timeouts and
revocation go through owned cleanup. Initial denial makes no remote calls.

Final evidence:
- Exact Google core image: 33 locked packages, 93 policies, 78 actual native
  SQL/crypto/queue/operator tests per PostgreSQL17/18, 20 qualification steps.
- Public Batch discovery revision20261103 pinned by SHA and provenance; generic
  independent schema walker verifies request fields/types/enums/read-only fields.
- 14 focused policies use native HTTP shape fixtures and real bounded filesystem
  operations. Actual UID transition is in the Linux pipeline, not host fchown mocks.
- Emitted three-stage Linux plan: 18 checks, actual DOCX and scanned PDF bytes,
  root/CHOWN-only download handoff, real credentialless parser, readonly upload
  mounts, matching byte-bound result consumer and private-volume cleanup. Native
  Google HTTP is scripted; local transfer stages also use network none.
- Exact new core image scan: 47 HIGH, 74 MEDIUM, 65 LOW, zero critical and no fixable
  HIGH/critical in the cached public DB. Security remains UNACCEPTED. This is not a
  new Java/parser vulnerability scan. Scanner version/binary hash/DB metadata kept.

Retain fixture/setup failures: host Python lacked requests or packaging until the
existing appropriate SDK/venv was selected; the first Linux pipeline did not keep
Docker stdin open for the synthetic HTTP fixture. Repair adds -i, not wider network
or capabilities. Retain the earlier qualified sources before stricter malformed
image/service-account/network validation. Final sources match final receipt hashes.

No real cloud job, VM identity/network behavior, account plan, deployment, native
startup/cancellation latency or complete private project is qualified. The default
production worker and generator capability remain disabled. Terraform/IAM/image
provenance wiring, durable orphan recovery and resource/data retention remain
unfinished; AWS/Azure/IBM native launchers, remaining medium/hard families and final
28-project/held-out evaluations remain required. No requirements were removed.
