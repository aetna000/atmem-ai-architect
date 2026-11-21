# Exact Cloud SQL proxy binary applicability review

Original Trivy inventory: one high, one medium and one unknown finding in module
versions used by the pinned upstream proxy. Do not delete or globally suppress them.

The repeatable qualifier extracts the exact Linux AMD64 binary from the immutable
image and retains its hash/build information. Official govulncheck v1.9.0 reports
only module matches, zero affected imported packages/symbols, and emits OpenVEX
not_affected / vulnerable_code_not_present for all three reviewed issues. A separate
Linux binary intentionally links the same affected HTML and OpenPGP packages;
the same scanner must detect every reviewed issue at compiled-symbol level. The
control is never executed or shipped to a client. Its older compiler's additional
standard-library findings belong to that intentionally affected control, not to
the upstream proxy, which was built with Go 1.27.3.

Raw scanner JSON, text, OpenVEX, control source/lock, tool build information and a
derived OpenVEX record bound to the exact image/platform/binary are retained. JSON
exit zero alone is not a pass: the qualifier checks actual finding contents and
positive-control detection. Any new finding or changed image needs another review.
The module inventory remains true; this resolves applicability only for these
three findings and this artifact. It is not a claim of complete security, native
Cloud SQL connectivity, IAM, TLS, cloud plan or deployment.

Compiler emission includes the bounded exact dependency review and rejects an
image/review mismatch. Nine targeted tests, all 302 JavaScript tests, build and the
fresh Google native schema/six mock plans pass. Full invoice operator delivery,
IBM adapter parity, whole-project admission and the full 28-case goal remain work.

Primary documentation:
- https://pkg.go.dev/golang.org/x/vuln/cmd/govulncheck
- https://pkg.go.dev/vuln/GO-2026-5932
- https://pkg.go.dev/vuln/GO-2026-6860
- https://pkg.go.dev/vuln/GO-2026-6866
