# Actual live invoice exports: native and portable qualification

The fresh IBM conversation after the canonical-region producer fix completed in
three exchanges, with one business question, zero technical questions and zero
internal response repairs. Its original export is preserved under `ibm-case/`.
The independent static assessment found no issues. Earlier AWS/Azure/Google original
cases remain in `../20261110-invoice-live-v2/cases/`.

`qualify-invoice-cloud.mjs PROVIDER FRESH_OUTPUT --case ORIGINAL_CASE` now admits
only original receipted Terraform/application bytes that reproduce the reviewed
compiler. It copies those exact bytes to a fresh qualification directory; it does
not modify a client handoff. Reproduction is execution admission, not a quality
score. Native Terraform schema validation and the exported mock plans provide
separate evidence. Six regression tests reject corrupt/mutated inputs, provider
mismatches, incomplete inventories and symlinks.

All four live artifact sets passed init with backend disabled and lockfile readonly,
provider validation, and native mock plans. Portable Linux test images were built
from their copied original application sources and tested sequentially against the
owned loopback PostgreSQL 18 fixture. Image identities, exact source hashes, pinned
test dependency versions and individual acceptance logs are preserved here.

No cloud credentials, account plan, apply, image publication or deployment ran.
Portable tests use explicit identity/storage/model/accounting fixtures. Actual
OCR/model semantics, composed end-to-end behavior, recovery and security review of
the exact live packages still require reconciliation before counting medium cases.
Known prior image-security findings remain open. The other medium/hard families,
final 28-case and held-out evaluation remain unfinished.
