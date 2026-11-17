# AtMem Architecture Review for coding agents: build plan

**One line:** a read-only architecture gate that spec-driven agents must pass between *plan* and *tasks*. It checks the plan (and optionally `terraform show -json` output) against a machine-readable `architecture.md`: budget, regions, data residency, uptime, approved services, network rules and ADRs. It never edits files, never runs Terraform, and never touches a cloud account.

Sources were read at **github/spec-kit @ e210504 (2026-11-16)**, cloned to `/workspace/research/spec-kit`, and **Fission-AI/OpenSpec @ f085c85 (2026-11-17)**, cloned to `/workspace/research/OpenSpec`. Paths below are relative to those clones.

---

## 1. Hook points (verified)

### spec-kit has a real extension and hook system, and we use it
- **How commands work:** each command is a markdown prompt with YAML frontmatter (`description`, `handoffs`, `scripts`) in `templates/commands/*.md` (plan, tasks, implement, analyze, checklist, clarify, constitution, converge, specify). `plan.md` runs `scripts/bash/setup-plan.sh --json`, then reads the spec and `/memory/constitution.md` (`templates/commands/plan.md:62-64`). It writes `research.md`, `data-model.md`, `contracts/` and `quickstart.md` (`plan.md:114-159`, tree in `templates/plan-template.md:47-57`). It also fills a **Constitution Check** gate (`plan-template.md:39`).
- **Hooks:** every core command template reads `.specify/extensions.yml` itself and surfaces `before_<cmd>` and `after_<cmd>` hooks. Plan's post-hooks are at `templates/commands/plan.md:74-106`, and tasks' pre-hooks at `templates/commands/tasks.md:30-56`. A hook with `optional: false` emits `EXECUTE_COMMAND:`, and the agent must run it and "wait for the result… before proceeding". The event list is in `docs/extensions/api.md:678-695` (`before_tasks` and `after_plan` both exist). Hook fields are in `api.md:743-755`.
- **Extensions:** an extension is an `extension.yml` plus `commands/*.md`. Commands must be named `speckit.<ext-id>.<cmd>` (`extensions/template/extension.yml:51-59`), and hooks are declared in the manifest (`:73-96`). Helper scripts with `../../scripts/...` resolve to the project's core scripts, and `{SCRIPT}` and `__SPECKIT_COMMAND_X__` get rendered (`docs/extensions/developing.md:318-397`). Config lives at `.specify/extensions/<id>/<id>-config.yml` (`developing.md:422-430`).
- **Install into agents:** the command is `specify init <proj> --integration <key>` or `specify integration install <key>`. Commands become skills at `.claude/skills/speckit-<cmd>/SKILL.md` (`docs/integrations/claude.md:21-24`), `.cursor/skills/…` (`cursor-agent.md:21-24`), `.agents/skills/…` for Codex, invoked as `$speckit-…` (`codex.md:21-24`), and `.github/skills/…` for Copilot (`copilot.md:22`).
- **Experimental MCP:** `specify mcp` is stdio-only and has read-only tools: `specify_version`, `specify_artifact_list/info` and `specify_workflow_list` (`docs/overview/mcp.md`). It only introspects Spec Kit and has no review or plan hooks, so it isn't useful as our hook point.
- **Our hook:** a mandatory **`before_tasks`** gate plus an optional **`after_plan`** nudge. ✅ **Tested:** `specify extension add --dev ./spec-kit` (CLI 1.4.2.dev0) installed cleanly. It registered both hooks in `.specify/extensions.yml`, rendered `.claude/skills/speckit-atmem-review/SKILL.md`, resolved `{SCRIPT}` to `.specify/scripts/bash/check-prerequisites.sh --json`, and scaffolded `.specify/extensions/atmem/atmem-config.yml`.

### OpenSpec has no extension or hook registry, but a custom schema gives a real gate
- **Flow:** `/opsx:propose` creates `openspec/changes/<name>/` with `proposal.md`, `specs/**/spec.md`, `design.md` and `tasks.md` in one step. Then come `/opsx:apply` and `/opsx:archive` (`docs/commands.md`). Expanded commands are `/opsx:new`, `continue`, `ff`, `verify` and others. Command and skill paths for each tool are listed in `docs/supported-tools.md:65-106`, e.g. Claude `.claude/commands/opsx/<id>.md`, Cursor `.cursor/commands/opsx-<id>.md` and Codex `.agents/skills/openspec-*/SKILL.md`.
- **Customization:** `openspec/config.yaml` takes `context`, `rules` and `operations`, but these are explicitly "not an enforceable check" (`docs/customization.md:127`). Custom schemas live in `openspec/schemas/<name>/schema.yaml` and are DAGs of artifacts linked by `requires` (`customization.md:163-345`). The docs even show "Adding a Review Artifact" (`customization.md:382-409`). The default schema is `schemas/spec-driven/schema.yaml`.
- **Our hook:** the schema `atmem-reviewed` is `spec-driven` plus a `review` artifact (requires specs and design), with `tasks` changed to require `review`. ✅ **Tested** with OpenSpec CLI 2.1.0: `schema validate` passes, and `openspec status` shows `tasks (blocked by: review)` until `review.md` exists. On FAIL the instruction writes `review.blocked.md` instead, so tasks stay blocked by the dependency graph.
- **Caveat:** `/opsx:propose` treats status as "file-existence only" and says dependencies are "enablers, not gates" when a *conditional* dependency was skipped (`src/core/templates/workflows/propose.ts:133-137`). Our `review` isn't conditional, so this exception shouldn't apply, but the gate is still enforced by the agent's prompt, not by code.

### Competition inside the catalogs (checked)
- The spec-kit community catalog has 202 extensions. Several are architecture-flavoured: `adrkit` ("checks produced plans against [decisions]"), `agentstandards` ("architecture council between planning and task generation"), `architecture-guard`, `arch-governance`, `security-review` and `plan-review-gate` (`extensions/catalog.community.json`).
- **None mention Terraform, Infracost, OpenTofu, Pulumi, CloudFormation, data residency or FinOps.** I grepped the catalog and `docs/community/*.md` for those terms and got zero hits.
- OpenSpec community schemas `anvil` (adversarial review) and `intent-driven` (ADR manifest) are listed in `docs/customization.md:421,425`.
- **Positioning:** don't sell "architecture review" in general, because ADR and drift checks are crowded. Sell **"the infra and cost gate: budget, region/residency, public exposure, approved services, checked against the actual Terraform plan."**

---

## 2. MCP tool `review_plan` (read-only)
- **Input** (`mcp/review_plan.input.schema.json`): `workflow`, `change_id`, `artifacts[] {kind, path, content}`, `rules {path, content}`, optional `terraform_plan {path, json}` (the `terraform show -json` format), and `options {fail_on, cost_estimate, currency, max_findings}`. Callers send **contents, not paths**, so the same tool works hosted.
- **Output** (`mcp/review_plan.output.schema.json`): `verdict` is pass, warn or fail. `violations[]` each have a `rule_id`, a severity and `evidence[]` (file and line with a verbatim excerpt, or a Terraform address, attribute and value). The output also has `cost {status, engine, monthly_total, budget_monthly, over_budget, top_resources}`, `risks[]`, `suggested_fixes[]` (never applied), `unverified[]` and `reviewer`.
- **Verdict rule:** any error-severity violation means fail. Warnings, or must-rules that can't be verified, mean warn. Otherwise pass. With `fail_on=warning`, warnings also fail.
- **Engine:** most of it is AI Architect logic you already have. Deterministic checks run on the Terraform JSON (attributes, regions, resource types). An LLM handles plan-prose checks and ADR conflicts, and it must cite lines.
- **Cost:** call Infracost when a plan JSON is present. Its current CLI uses `infracost scan tfplan.json --json` and needs `infracost auth login` or the `INFRACOST_CLI_AUTHENTICATION_TOKEN` env var ([Infracost CLI docs](https://www.infracost.io/docs/features/cli_commands/)). Note that Infracost now ships its own agent skills (`infracost agent setup`), so it's a partner on cost, not on architecture.
- ✅ Both sample payloads validate against the schemas (`examples/review-input.sample.json`, `examples/review-output.fail.json`).

## 3. Rules file: a separate `architecture.md`, referenced from constitution.md
**Recommendation: don't reuse `constitution.md` for the rules.**
- It's free-form prose principles (`templates/constitution-template.md`), and `/speckit.constitution` overwrites it (`templates/commands/constitution.md:127`).
- OpenSpec has no equivalent, and its `config.yaml` rules aren't enforceable.

**Use instead:** `architecture.md` with YAML front matter for machine rules and markdown ADRs underneath (`examples/architecture.md`).
- Rule groups: `budget`, `regions`, `data_residency`, `uptime`, `services`, `network` and `exceptions`.
- Each rule has an `id` and a `severity`. ADRs use `ADR-NNNN` IDs with a status.
- Default paths are `.specify/memory/architecture.md` for spec-kit and `openspec/architecture.md` for OpenSpec.
- Add one constitution principle: "Infrastructure must satisfy `.specify/memory/architecture.md`; enforced by /speckit.atmem.review."

## 4. Ready-to-use hooks (files)
- **spec-kit:** `spec-kit/extension.yml` (id `atmem`, which is free in the catalog) and `spec-kit/commands/speckit.atmem.review.md`.
  - Invocation: `/speckit-atmem-review` in Claude Code and Cursor, `$speckit-atmem-review` in Codex.
  - It reads `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, the constitution and the rules, plus an optional plan JSON. It then calls `review_plan`, writes only `architecture-review.json`, and on FAIL stops `/speckit.tasks`.
  - Supporting files: `config-template.yml` and `README.md`.
- **OpenSpec:**
  - (A) Hard gate: `openspec/schemas/atmem-reviewed/` (a full fork with `templates/review.md`).
  - (B) Manual step: `openspec/command/atmem-review.md`, a standalone `/atmem-review` command, deliberately outside the OpenSpec-managed `opsx` namespace. Install table is in `openspec/command/INSTALL.md`.

## 5. 60-second demo
See `demo/DEMO-60s.md`. It uses spec-kit's own **Taskify** quickstart (`docs/quickstart.md`) with "deploy on AWS with Terraform" added. The plan quietly says `us-east-1`, a public RDS instance and `db.r6g.xlarge` Multi-AZ (`demo/plan.excerpt.md:13-15`, `demo/tfplan.excerpt.json`). Running `/speckit-tasks` fires the mandatory hook, which returns FAIL on NET-001, NET-002, REGION-001 and BUDGET-001, and no `tasks.md` gets created. After fixes it passes. ⚠️ The cost numbers in the sample JSON are hand-estimated and labelled illustrative, so swap in a real Infracost run before recording.

## 6. Distribution
- **spec-kit:** community extensions are accepted.
  - Submit through the **Extension Submission issue form only**. Direct catalog PRs get closed (`docs/extensions/publishing.md` "How to Submit", `.github/ISSUE_TEMPLATE/extension_submission.yml`).
  - Maintainers check metadata, not code.
  - The community catalog is **discovery-only**, so users install with `specify extension add atmem --from <zip>` (`docs/extensions/catalogs.md:8-45`).
  - Drafts are in `distribution/spec-kit.md`: the form answers plus a Show-and-tell Discussion post.
- **OpenSpec:** open an issue with the repo link and a one-line description, and a maintainer adds a row to the Community Schemas table (`docs/customization.md:429`). The draft is in `distribution/openspec.md`.
- **Nothing has been posted.**

## 7. Build order (about 2 weeks)
1. **Days 1-3:** deliver `review_plan` as an MCP server (stdio first, hosted later), wrapping AI Architect. Write deterministic Terraform-JSON checks for NET-001, NET-002, REGION, SVC and RESIDENCY, and add the Infracost call.
2. **Days 4-5:** add LLM checks for plan prose and ADR conflicts, with mandatory line citations. Validate output against the schema.
3. **Day 6:** publish `atmem-ai/spec-kit-atmem` (this `spec-kit/` folder plus LICENSE and CHANGELOG), tag v0.1.0, and test `--from` installs in Claude Code, Cursor and Codex.
4. **Day 7:** publish `atmem-ai/openspec-schemas` with `atmem-reviewed`.
5. **Day 8:** record the demo with real output.
6. **Days 9-10:** file the spec-kit submission and the OpenSpec issue, then post the demo on X.

## 8. Blockers and risks
- **The gate is enforced by the agent's prompt in both tools.** spec-kit hooks are instructions inside the command templates. The docs don't say a failed hook aborts the parent command, so our command explicitly tells the agent to stop. A determined user or agent can skip it. For a hard guarantee, add a CI check that fails when `architecture-review.json` says fail.
- **spec-kit `condition` is ignored by templates.** A hook with a non-empty condition is *skipped* (`api.md:755`), so keep `condition: null`.
- **The OpenSpec gate is file-existence only** (`propose.ts:133`). The `review.blocked.md` trick works with the graph, but an agent could still hand-write `review.md`.
- **The Terraform plan JSON must come from the user or CI.** `terraform plan` usually needs provider credentials, and the reviewer deliberately won't run it. Without a plan, cost is `skipped` and checks fall back to prose.
- **The spec-kit MCP is experimental** and has no hook surface, so we don't depend on it.
- **The catalog is crowded on generic architecture review** (`adrkit`, `architecture-guard` and others), so lead with the infra and cost angle.
- **Placeholder values** to replace before publishing: repo URLs (`atmem-ai/...`), the `speckit_version` floor (only tested on 1.4.2.dev0) and the MCP server name `atmem-architect`.

## Files
```
PLAN.md
mcp/review_plan.input.schema.json
mcp/review_plan.output.schema.json
spec-kit/extension.yml
spec-kit/commands/speckit.atmem.review.md
spec-kit/config-template.yml
spec-kit/README.md
openspec/schemas/atmem-reviewed/schema.yaml        (fork of spec-driven + review artifact)
openspec/schemas/atmem-reviewed/templates/{proposal,spec,design,tasks,review}.md
openspec/command/atmem-review.md
openspec/command/INSTALL.md
examples/architecture.md
examples/review-input.sample.json
examples/review-output.fail.json
demo/DEMO-60s.md
demo/plan.excerpt.md
demo/tfplan.excerpt.json
distribution/spec-kit.md
distribution/openspec.md
```
