# External sources and channels

Open [project.atmem-ai-architect.json](project.atmem-ai-architect.json) using **⋯ → Open project file** in AtMem Architect. [Diagram](diagram.svg).

## Prompt and refinement history

Exact submitted prompts and responses are in [history/2026-11-07T05-56-30.120Z](history/2026-11-07T05-56-30.120Z), in round order. The selected project and Terraform come from round 2. Changing a prompt may produce a different architecture; these are captured outputs, not deterministic model guarantees.

## Recorded results

- Local exported-artifact checks: **passed**.
- Actual AWS account plan: **passed**.
- Account preflight: **blocked**.
- This exact export deployed: **not_run**.
- This exact export cleanup: **not_run**.

## Live acceptance still required for this export

- [ ] Approved source connection synchronizes documents
- [ ] Source deletes and ACL changes propagate
- [ ] Source outage retries and recovers
- [ ] Authenticated channel preserves identity and citations

See [the shared runbook](../RUNBOOK.md) for local reproduction, account checks, deployment gates and cleanup. Model outputs in history are design evidence, not authoritative test results. Local application tests use mocks; AWS model availability checks do not invoke the model.
