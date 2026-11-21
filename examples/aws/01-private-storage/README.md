# Private document storage

Open [project.atmem-ai-architect.json](project.atmem-ai-architect.json) using **⋯ → Open project file** in AtMem Architect. [Diagram](diagram.svg).

## Prompt and refinement history

Exact submitted prompts and responses are in [history/2026-11-07T05-49-19.638Z](history/2026-11-07T05-49-19.638Z), in round order. The selected project and Terraform come from round 2. Changing a prompt may produce a different architecture; these are captured outputs, not deterministic model guarantees.

## Recorded results

- Local exported-artifact checks: **passed**.
- Actual AWS account plan: **not_run**.
- Account preflight: **not_run**.
- This exact export deployed: **not_run**.
- This exact export cleanup: **not_run**.

An earlier storage project passed live AWS tests and cleanup. Its exact project, generated configuration and receipt are retained under evidence/live; that result is not transferred to this newer export.

## Live acceptance still required for this export

- [ ] Authorized upload/download preserves bytes
- [ ] Unauthenticated access is denied
- [ ] Versioning/encryption/public-access settings verified
- [ ] Approved cleanup leaves no scenario resources

See [the shared runbook](../RUNBOOK.md) for local reproduction, account checks, deployment gates and cleanup. Model outputs in history are design evidence, not authoritative test results. Local application tests use mocks; AWS model availability checks do not invoke the model.
