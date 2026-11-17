# Installing the standalone /atmem-review command (OpenSpec projects)

OpenSpec has no extension/hook registry (see PLAN.md). Two options:

## A. Review artifact dependency: custom schema
Copy `../schemas/atmem-reviewed/` to `openspec/schemas/atmem-reviewed/` and set `schema: atmem-reviewed` in `openspec/config.yaml`.
`tasks` then requires `review`, so `openspec status` shows `tasks (blocked by: review)` until `review.md` exists (verified with OpenSpec CLI 2.1.0).

## B. Manual step: one command file
Copy `atmem-review.md` to the location your agent loads custom commands from. Use your own name, not the `opsx` namespace, which OpenSpec manages.

| Agent | Path | Invoke |
|---|---|---|
| Claude Code | `.claude/commands/atmem-review.md` | `/atmem-review` |
| Cursor | `.cursor/commands/atmem-review.md` | `/atmem-review` |
| GitHub Copilot (IDE) | `.github/prompts/atmem-review.prompt.md` | `/atmem-review` |
| Codex | `.agents/skills/atmem-review/SKILL.md` (add `name: atmem-review` to frontmatter) | `$atmem-review` |

Artifact existence is not proof of a valid or current review. Prompt enforcement can be bypassed; use the fresh CI gate from the package README. A failed re-review must archive an earlier current review report before writing review.blocked.md.
