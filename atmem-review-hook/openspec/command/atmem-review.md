---
description: "Read-only AtMem architecture review of an OpenSpec change (design.md + optional Terraform plan) against openspec/architecture.md. Run after /opsx:propose (or /opsx:continue reaches design) and before /opsx:apply."
---

# AtMem architecture review (OpenSpec)

Arguments: `$ARGUMENTS` — optional change name, optional path to a Terraform plan JSON, optional `--strict` (warnings fail).

This command is **read-only**. Never edit proposal.md, specs, design.md, tasks.md, Terraform or the rules file. Never run `terraform plan/apply` or touch a cloud account.

## Steps

1. **Pick the change.** If a change name was given, use it. Otherwise run `openspec list --json` and pick the single active change; if there are several, ask the user which one.
2. **Find its files.** Run `openspec status --change "<name>" --json` and read `changeRoot` and `artifactPaths` from it. Read `proposal.md`, `design.md` (may be absent; it is conditional in spec-driven), every delta spec under `specs/`, and `tasks.md` if it already exists.
3. **Load rules.** Read `openspec/architecture.md` (override: env `ATMEM_RULES_PATH`). If missing, report `WARN: no_rules_file` and stop.
4. **Optional Terraform.** If a plan JSON path was given (or env `ATMEM_TERRAFORM_PLAN_JSON`), read it. It must be `terraform show -json <planfile>` output; do not generate it.
5. **Call `review_plan`** (MCP server `atmem-architect`) with `workflow: "openspec"`, `change_id: <name>`, each artifact as `{kind, path, content}` (kinds: `proposal`, `spec`, `design`, `tasks`), `rules: {path, content}`, optional `terraform_plan: {path, json}`, and `options.fail_on` (`warning` if `--strict`, else `error`). Send contents, not just paths.
6. **Write one file:** `<changeRoot>/architecture-review.json` with the raw result.
7. **Report** verdict, a table of `rule_id | severity | finding | evidence`, estimated monthly cost vs budget (or why it was not estimated), suggested fixes, and rules that could not be verified. Quote rule IDs and numbers exactly.
8. **Gate.** On `fail`: say "Architecture review FAILED. Do not run /opsx:apply until design.md is fixed or an exception is recorded in architecture.md." Do not start implementation in this session. On `warn`/`pass`: say so and continue.

If the MCP tool is unavailable, report `WARN: reviewer_unavailable` and invent nothing.
