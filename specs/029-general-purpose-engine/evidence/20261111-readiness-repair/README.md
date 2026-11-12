# Independent browser journey exposed initialization race

Original primary AWS package e52bf0c7f33c9067ce55d29f701632d05cd90eef6e2376bd48f63407b74cd7ac
passes15 connected independent browser groups through actual packaged Python3.12
ARM64 handler, local authorization-code/S256-PKCE/RSA-gateway emulation and synthetic
Bedrock transport. Browser assets and Lambda code were unchanged. Only the exact
synthetic Cognito HTTPS origin is routed to the local emulator; no vendor requests
or account operations are used. Initial success is retained, not promoted to proof
of actual Cognito/MFA/JWKS lifecycle, model quality or complete project acceptance.

Extending the journey to another sign-in immediately after reload fails: the visible
Sign in control runs before config.json completes, uses undefined configuration and
reports unavailable. No page error is emitted because the app catches it. The
initial connected15 groups remain passed; logout/expiry groups are unexecuted after
this failure. The negative receipt is retained. A separate actual Chromium oracle
stalls configuration until the initial user interaction, then resolves it. The
unchanged package deterministically fails to reach the synthetic OAuth endpoint.
This is a missing initialization prerequisite, not an identity-provider outage.

The reusable engine guidance now requires explicit asynchronous prerequisites,
disabled or safely retained dependent actions, actual immediate/delayed/failed
initialization/reload/recovery browser checks and usable retries. It contains no
workload/provider identifiers, code answer or fixed recipe. The independent startup
oracle is an evaluation-only adapter for this observed package layout, not a
production dispatcher or generality claim.

Subsequent [native repair and independent verification](repaired/README.md) preserve
the original session/pins and expose two remaining delivery gaps. The evaluator
never edited generated files. A separate [new-domain file-viewer transfer](new-domain-transfer/README.md)
passes31 independent browser/file checks. Keep the coached AWS repair distinct from
the original uncoached generation and the new-domain brief. Next qualify generic
dependency/runtime capability and available machine-readable safety preconditions,
then package the versioned local candidate. Counts remain0/28 and0/10.
