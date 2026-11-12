# IBM application and exact-image qualification checkpoint

This is one live IBM ticket-triage case, not the completed 28-project evaluation.
All six business fact categories were delivered. It converged in three exchanges,
one country question, zero technical questions, in 228.01 seconds. The original
export and subsequent compiler-only regenerations are preserved separately.

The exact original v13 package passed independent static assessment, dependency
closure, emitted Python 3.13 application checks, native provider schema and four
mock-plan checks. The corrected v15 export additionally admits/tests the stated
five-request burst and exercises its actual four-field schema through the model
transport. Its Linux/amd64 image runs nonroot/read-only with networking disabled;
startup, unsigned denial and all 15 emitted acceptance checks passed. These include
real local RSA signatures, HTTP boundaries, pinned SDK construction and scripted
IBM model transport. They do not establish live IBM authentication or inference.

Azure and Google full-business-brief projects were regenerated without changing
their design or earlier conversation. Their v16 exact source/provider checks and
Linux image startup/actual-schema checks passed, with 18 and 12 emitted checks.
Azure now requests the documented strict JSON Schema response format; its selected
model/version must support it. No unsupported schema fallback is attempted.

Security scanning exposed issues in the prior Bookworm base and installer tools.
The common generator now uses a digest-pinned Trixie base, a hash-pinned zlib update
verified against Debian's signed security indexes, and removes pip/ensurepip after
installing runtime wheels. No SBOM was deleted to conceal findings. Each latest
exact Azure/Google/IBM image scan reports zero critical findings, 47 high findings
without a reported fix, and zero high findings with an available fix. The remaining
findings are open security work; this is not a clean vulnerability pass. Full old
and new reports are retained, including failed attempts.

The current IBM SDK requires dateutil 3, incompatible with the AWS SDK's constraint.
An attempted shared install exposed that conflict; it was reversed, and the server
dependency check is clean. IBM emulation now uses its own hash-locked Python 3.13
worker. A missing worker reports unavailable rather than skipping its SDK check.

Regression evidence: 274 JavaScript tests, 158 server tests and the build pass;
seven IBM browser fixture checks and six shared-browser checks pass. Production
state/operations, remaining image vulnerabilities, live identity/model quality,
regional availability/quota/costs, authorized account plans and medium/hard system
behavior remain unverified. No cloud deployment, image publication or repository
push occurred. The full 28-case rerun and held-out acceptance remain pending.

Failed attempts retained include the first knowledge-record provenance error,
invalid Code Engine visibility value, a test assumption about Azure's response
format and the initial shared dependency conflict. Fixes were made in the engine,
source templates or qualification harness; original exports were not patched.
