# Reviewable release candidate

Stable proposed version: 0.1.0. This is a local candidate; no public publication is authorized or claimed.

Artifacts:
- Python wheel `atmem_architecture_review-0.1.0-py3-none-any.whl`
- Spec Kit extension archive `spec-kit-atmem-0.1.0.zip` (manifest at archive root)
- OpenSpec archive `openspec-atmem-reviewed-0.1.0.zip`

Use a separate future tag such as `review-hook-v0.1.0`; an Architect `v*` tag can trigger the existing npm release workflow. This package is independently distributed and does not change `@atmem/architect` version.

## Manual card

1. Install the wheel into a fresh Python virtual environment.
2. Run the supplied sample through `atmem-review`: expect exit 1 and REGION-001, NET-001, NET-002. Budget remains unpriced without an enabled qualified pricing engine.
3. Run `demo/generated/after.input.json`: expect WARN, not PASS; inspect retained budget/residency/uptime/ADR unknowns.
4. Add `options.fail_on: warning` to that request: expect exit 1.
5. Connect `atmem-review-mcp` to a client: exactly one read-only `review_plan` tool. A citation path must not cause server filesystem reads.
6. Install the Spec Kit extension in a disposable project: mandatory `before_tasks`, optional `after_plan`, rendered agent command and config scaffold.
7. In OpenSpec, absent/current-failed review keeps tasks blocked. WARN allows the review artifact with default policy. A failed re-review archives the old report so it cannot unlock tasks.
8. Run fresh CI against current files; change a known private database flag to public. Expect failure without consulting any prior report JSON.

## Remaining publication gates

- Broader pricing coverage: CLI 2.19.1 now has one credential-backed EC2/gp3 qualification with actual under/over-budget decisions ([evidence](../specs/033-architecture-review-hook/evidence/live-pricing.json)); other services/providers/currencies remain unqualified.
- Live explicitly approved model evaluation of representative prose/ADR cases, with usage and citation-quality evidence.
- Installed client/platform CI and independent code review.
- Owner authorization for tags, public package/catalog submissions or hosted service deployment.

The Spec Kit/OpenSpec registrations and file dependencies are qualified independently of agent obedience. Neither provides an unbypassable security guarantee. Customer-selected rules and generated plan JSON can contain sensitive data; external adapters stay disabled by default.

Rollback removes the extension/schema selection and local MCP connection. There are no cloud resources, infrastructure state changes or customer artifact rewrites to undo.
