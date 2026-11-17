# Final read-only confirmation

Model: Claude Opus5.5; effort:medium; tools disabled. Round2 reviewed complete revised documents. Round3 reviewed only final clarification delta, not a new full-file pass.

**AGREE. No blockers.**

I based this on the clarification text above, as you asked (no tools). I did not re-read the spec files. The clarifications are consistent with each other and resolve the N1–N10 notes without changing release order.

**Egress:** Binding to an immutable source-selection digest, rather than to each request payload, is the right granularity. Repair requests can only use the confirmed selection, sanitized verifier findings and prior model output. Each one gets its own payload digest and filter receipt, so derived requests stay auditable. Changes to bytes, path, data class, backend or terms correctly force reconfirmation. R4 stopping at `egress_confirmation_required`, while inventory and matching recur unattended, keeps the boundary clear. Deferring standing egress policy to a separately approved extension is correct.

**Broker and refs:** The broker enforces the `refs/heads/atmem-upgrades/` prefix plus the campaign-ownership ledger independently of token scope. It denies default, protected and unowned refs even in unprotected repos. That closes the gap where a token's scope is broader than intended. Other strong choices:
- read-only PR base
- one token per resource owner, with explicit approval and expiry states
- fail-closed publication when no qualified keychain is available
- never requesting workflow permission
- SHA/provenance detection instead of author identity
- stopping for reconciliation on a competing campaign

**Source policy and automation disclosure:** Allowing only exact recipe sources plus an equality-passing current ReleaseObservation module ref is tight. Detecting `pull_request_target`, `workflow_run`, `check_suite` and required-check apps, with explicit disclosure of unknown automation, is appropriate. Measuring and publishing R0 coverage limits keeps waivers from being silent.

**Tests:** T001, T006, T013, T016 and T017 map directly to the new invariants.

Optional nonblocking suggestions:
- Define "current" for ReleaseObservation, such as a freshness window or re-observation at publication time, so a stale observation can't authorize a module ref.
- State that sanitization of prior model output and verifier findings uses the same filter that issues the receipt.
