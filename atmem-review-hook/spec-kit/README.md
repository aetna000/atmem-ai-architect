# AtMem review gate for Spec Kit

Local development candidate. Install from the `spec-kit/` directory in this source checkout; no public extension release is claimed.

From a project initialized with Spec Kit (locally tested: **1.0.4**):

```sh
specify extension add --dev /absolute/path/atmem-review-hook/spec-kit
```

If the project has no architecture policy yet, copy `atmem-review-hook/examples/architecture.md` to `.specify/memory/architecture.md` and edit its rules. The extension archive also includes this sample at `.specify/extensions/atmem/examples/architecture.md`. Preserve an existing team policy. The extension scaffolds `.specify/extensions/atmem/atmem-config.yml` automatically.

Install and connect the [reviewer MCP server](../README.md) as `atmem-architect`.

- `/speckit.tasks` requests the mandatory `before_tasks` review.
- `/speckit.plan` offers the optional `after_plan` review.
- Manual: `/speckit-atmem-review` in Claude Code/Cursor; `$speckit-atmem-review` in Codex.

The reviewer accepts content, returns exact evidence and never edits plans, runs Terraform or calls a cloud-provider account. The agent wrapper writes `architecture-review.json` only. Default policy: errors fail; missing rules/reviewer/pricing or unsupported checks warn. `--strict` / `fail_on: warning` makes unknowns block.

Hooks are agent instructions, not executable enforcement of task creation. A skipping agent or malformed hook registration can bypass them. Use the fresh [CI gate](../README.md#fresh-ci-gate) to enforce your policy independently of an agent's report file.

Rollback: `specify extension remove atmem`; remove the reviewer MCP connection if no longer needed. Existing infrastructure and source remain untouched.
