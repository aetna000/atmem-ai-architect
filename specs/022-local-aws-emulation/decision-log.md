# Decisions and observed gaps

- User requested strong AWS emulation, available in AtMem Architect before download, with future website deployment in mind. Use a server-only worker behind a relative API, with an explicit future hosted isolation boundary.
- Existing milestone and example archive were already committed/pushed (96e369d and 8c7e7a3) before this increment. Preserve old example evidence.
- Docker CLI exists but no daemon was available; current disk space also disfavors large container/model downloads. Choose optional pinned Moto 5.2.5 for stateful service APIs. LocalStack remains an additional unqualified backend, not an installed capability.
- Actual generated Python handlers execute on the host. Never use Moto Dockerless Lambda's assumed-success result. Bedrock and authorizer contexts are explicit fixtures; no cloud writes or real inference.
- First seven-scenario run failed async processing: Moto omitted object version IDs in standard S3 notifications. Independently reproduced against unpatched Moto and checked the AWS notification specification. Add exact-triggering-version adapter v1, with two-version delayed-consumption regression coverage. Do not relax the application requirement for exact versions.
- Second run exposed a harness error: the consumer parsed poison JSON before invoking the handler. Fix the harness so the generated handler classifies it, then exercise actual Moto redrive. Keep both failed reports.
- Read generated notification, partial batch mapping and redrive contracts instead of silently inventing missing infrastructure wiring. Fault-injection tests confirm missing triggers and broken handlers fail emulation.
- Corrected runs pass all seven supported workflows, including actual DynamoDB conditional writes, source interruption recovery and source permission-lease expiry. Resource types not emulated remain enumerated. No Terraform apply, IAM policy enforcement, native vendor compatibility, hosted isolation or production qualification is claimed.
- Browser end-to-end check proves emulation before download, downloadable reports, exact per-file equality with the delivery ZIP, and removal of stale results on project change.
