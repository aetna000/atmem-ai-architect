---
description: "Read-only architecture gate: review plan.md (and an optional Terraform plan) against the project's architecture.md rules before tasks are generated."
tools:
  - 'atmem-architect/review_plan'
scripts:
  sh: ../../scripts/bash/check-prerequisites.sh --json
  ps: ../../scripts/powershell/check-prerequisites.ps1 -Json
  py: ../../scripts/python/check_prerequisites.py --json
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty). Accepted inputs: a path to a Terraform plan JSON file, `--rules <path>`, or `--strict` (treat warnings as failures).

## Purpose

This command is a **read-only** architecture review. It never edits `plan.md`, never writes Terraform, never runs `terraform plan/apply`, and never touches a cloud account. It reads the current feature's design artifacts, sends them to the `review_plan` MCP tool, and reports a verdict. When it runs as the `before_tasks` hook, a `fail` verdict means **task generation must stop**.

## Steps

### 1. Locate the feature

Run `{SCRIPT}` from the repo root and parse its JSON for `FEATURE_DIR` and `AVAILABLE_DOCS`. If it errors (no feature directory or no `plan.md`), report the error and stop. All paths below are absolute.

### 2. Load configuration

Read `.specify/extensions/atmem/atmem-config.yml` if it exists; otherwise use these defaults:

- `rules_path`: `.specify/memory/architecture.md`
- `terraform_plan_json`: empty
- `fail_on`: `error`
- `cost_estimate`: `auto`

Environment variables override the file: `SPECKIT_ATMEM_RULES_PATH`, `SPECKIT_ATMEM_TERRAFORM_PLAN_JSON`, `SPECKIT_ATMEM_FAIL_ON`. Arguments from User Input override both (`--rules`, a `*.json` path, `--strict` = `fail_on: warning`).

If the rules file does not exist: tell the user the review cannot run without `architecture.md`, point them to the sample in the extension README, and stop **without** blocking (report verdict `warn`, reason `no_rules_file`).

### 3. Collect artifacts (read only)

Read these files if present and keep their full text:

- `FEATURE_DIR/plan.md` (required)
- `FEATURE_DIR/spec.md`
- `FEATURE_DIR/research.md`
- `FEATURE_DIR/data-model.md`
- every file under `FEATURE_DIR/contracts/`
- `.specify/memory/constitution.md`
- the rules file
- the Terraform plan JSON, if configured (this must be the output of `terraform show -json <planfile>`; do **not** generate it yourself)

### 4. Call the reviewer

Call the MCP tool `review_plan` with:

```json
{
  "workflow": "spec-kit",
  "change_id": "<basename of FEATURE_DIR>",
  "artifacts": [
    { "kind": "plan", "path": "specs/<feature>/plan.md", "content": "<full text>" },
    { "kind": "spec", "path": "specs/<feature>/spec.md", "content": "<full text>" },
    { "kind": "research", "path": "...", "content": "..." },
    { "kind": "data-model", "path": "...", "content": "..." },
    { "kind": "contract", "path": "...", "content": "..." },
    { "kind": "constitution", "path": ".specify/memory/constitution.md", "content": "..." }
  ],
  "rules": { "path": "<rules_path>", "content": "<full text>" },
  "terraform_plan": { "path": "<terraform_plan_json>", "json": <parsed JSON> },
  "options": { "fail_on": "<fail_on>", "cost_estimate": "<cost_estimate>" }
}
```

Omit `terraform_plan` when none is configured. Use project-relative paths. Send file contents, not just paths: the reviewer may run remotely and cannot read the local disk.

If the tool is unavailable or errors, say so plainly, report verdict `warn` with reason `reviewer_unavailable`, and do not invent findings.

### 5. Report

Save the raw tool result to `FEATURE_DIR/architecture-review.json` (this is the only file this command writes). Then print:

```
## Architecture Review: <PASS | WARN | FAIL>

<summary>

| Rule | Severity | Finding | Evidence |
|------|----------|---------|----------|
| <rule_id> | <severity> | <title> | <path>:<line> or <resource_address> |

Estimated monthly cost: <monthly_total> <currency> (budget <budget_monthly>) — or "not estimated: <reason>"

Suggested fixes:
1. <rule_id>: <change>

Not verifiable from these artifacts: <unverified list, if any>
```

Quote evidence exactly as returned; do not paraphrase rule IDs or numbers.

### 6. Gate

- **fail**: State clearly: "Architecture review FAILED. Do not generate tasks." If this command was invoked as a `before_tasks` hook, **stop the `/speckit.tasks` run now**: do not create or modify `tasks.md`. Tell the user to fix `plan.md` (or the Terraform), or to record an accepted exception in the rules file's **Exceptions** section, then re-run `__SPECKIT_COMMAND_PLAN__` or this command.
- **warn**: Show the warnings and continue. If `fail_on` is `warning`, treat as fail.
- **pass**: Say so in one line and continue.

Never edit `plan.md`, the rules file, or Terraform to make the review pass. Fixes are the user's (or a later command's) decision.

## Done When

- [ ] Verdict reported with every violation's rule ID and evidence
- [ ] `architecture-review.json` written to the feature directory
- [ ] On `fail` during `before_tasks`, task generation did not proceed
