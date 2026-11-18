# Native integration manual check

Use the existing Architect workspace and a disposable project.

1. Open Review → Architecture rules. Save an allowed region or private-storage rule to AtMem.
2. Run the design review. Activity should appear immediately; inspect exact findings.
3. Make a violating design/rule change. The review must fail; Code it must not accept that stale or failing design.
4. Correct it and rerun. Save the project, then use Code it with the existing coding adapter.
5. Inspect Spec Kit → Code → Tests → Infrastructure, current task IDs and captured files. A file link must not claim a passed test.
6. Change a requirement/rule and inspect the earlier mappings/results: previous evidence must not approve the changed input.
7. Reopen the project and ask chat where work stands. AtMem should supply recorded facts with their evidence limits.

Automated qualification covers steps 1–3, persistence, conflicting editors, mobile controls, backend handoff/binding/validation contracts and clean installation. Steps 4–7 together still require a complete live native implementation acceptance run.

Rollback: return to the previous branch commit caeb49a with a clean separate checkout and reinstall its candidate. Keep the current AtMem/project data; no destructive migration is required. Do not overwrite an active worktree or delete memory to roll back.
