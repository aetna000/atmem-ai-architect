# Implementation plan

Base: origin/main 7601a8e. Worktree: architect-review-hook; branch feat/architecture-review-hook. R3 remains separate.

Build the reviewer as a small independently installable Python package under the supplied folder, using existing pinned jsonschema, PyYAML and MCP dependencies. Keep the original PLAN.md as supplied evidence. Reuse Architect's backend-neutral contract and verification discipline, not its stateful generation pipeline: a review must not create project memory, run provider binaries or execute source hooks.

Implement bounded policy parsing, effective Terraform desired-state traversal and evidence-first checks; cost/model adapters are explicit operator opt-ins. Model output is advisory evidence validated independently and cannot clear deterministic violations or unknown infrastructure facts. A supplied plan snapshot is not proof of deployment, account state or actual uptime.

Test positive, negative and unknown cases, child modules/aliases, destroys, computed values, malformed/hostile rules, exceptions, budget currency/coverage and prompt injection. Exercise actual stdio initialization/tools/call via the installed SDK. Test CLI/CI artifact binding and install both workflow adapters into disposable local projects. Record exact versions and distinguish fake cost/model adapters from live vendor evidence.

Package a local candidate and create a reviewable PR. Do not tag/publish/deploy or submit public catalog messages without the owner's publication instruction.
