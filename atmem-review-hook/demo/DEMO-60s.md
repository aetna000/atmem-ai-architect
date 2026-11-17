# Proposed 60-second demo: "Your agent's plan looked fine. It wasn't."

**Current evidence:** `generated/` contains actual engine results: FAIL before fixes, WARN afterward. No live cost estimate or agent-obedience recording exists. The storyboard below remains a proposal; its illustrative dollar figure is not measured output.

**Base:** the public **Taskify** example from Spec Kit's own quickstart (`docs/quickstart.md` in github/spec-kit), run in Claude Code. One tweak: the `/speckit-plan` prompt adds "deploy on AWS with Terraform".
**Prepared beforehand (off camera):** `specify init taskify --integration claude`, `/speckit-constitution` and `/speckit-specify` from the quickstart, `specify extension add --dev ./spec-kit-atmem`, `examples/architecture.md` copied to `.specify/memory/architecture.md`, the `atmem-architect` MCP server connected, and `infra/tfplan.json` from `terraform plan -out tfplan && terraform show -json tfplan > infra/tfplan.json` (produced locally/emulated; the reviewer never runs Terraform).

| Time | Screen | Voice-over / caption |
|---|---|---|
| 0–6s | Terminal title card: "Spec Kit + one read-only check" | "Coding agents now write the plan before the code. Who checks the plan?" |
| 6–15s | `/speckit-plan Use .NET Aspire with Postgres… deploy on AWS with Terraform` → plan.md appears. Scroll past the Constitution Check: "Security-First ✅" | "Claude writes a clean plan. Constitution check: all green." |
| 15–22s | Zoom on plan.md lines 13–15 (`us-east-1`, `db.r6g.xlarge Multi-AZ`, `publicly_accessible = true`) — subtle, mid-paragraph | "Three lines nobody reads." |
| 22–30s | Type `/speckit-tasks`. Output shows `**Automatic Pre-Hook**: atmem` / `EXECUTE_COMMAND: speckit.atmem.review` | "Before any task is written, the architecture gate runs. Automatically." |
| 30–45s | Review table: `FAIL` · NET-001 public RDS (plan.md:15, `aws_db_instance.main.publicly_accessible = true`) · NET-002 5432 open to 0.0.0.0/0 · REGION-001 us-east-1 (PII must stay in AU) · BUDGET-001 ≈ $790/mo vs $150 | "Public database. Wrong country for customer data. Five times over budget. Every finding cites the line and the rule." |
| 45–52s | "Architecture review FAILED. Do not generate tasks." — `tasks.md` is not created (`ls specs/001-taskify/`) | "No tasks. No code. Nothing touched your cloud." |
| 52–58s | Ask Claude "apply the suggested fixes to plan.md", re-run → `PASS · ≈ $X/mo` | "Fix, re-run, pass." |
| 58–60s | End card: `specify extension add atmem --from <release zip>` · atmem.ai (community catalog is search-only; installs need `--from`) | "AtMem: the architecture check your agent must pass." |

**Recording notes**
- Use real output only. Before recording, run Infracost on the demo plan and replace the illustrative ≈$790 with the real number (the sample JSON in `examples/` is hand-estimated).
- Keep the Constitution Check "✅" visible: it shows the gap the review fills (plan.md checks principles, not resources).
- Optional OpenSpec cut (15s): `/opsx:propose add-taskify-db` with `schema: atmem-reviewed` → `openspec status` shows `tasks (blocked by: review)` after a FAIL.
