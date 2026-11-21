# Azure invoice adapter checkpoint

Seven native Terraform mock plans and provider-schema checks pass for the new
private invoice composition. This is an isolated compiler fixture, not a completed
client conversation or cloud deployment. API/worker/private parser, Entra roles,
private native database/storage/model/secret connections and operator outputs are
emitted. Native operator scheduling/bootstrap and whole-project registry/Spec Kit
admission remain unfinished. Actual emitted-environment image checks are next.

The parser enforces signed app-only Entra tokens for its exact tenant, audience,
worker client/principal and Parser.Invoke role before reading PDF input. Five real
local RSA/JWT/RPC tests and nine existing/extended TLS/client tests pass. The locked
Linux parser image passes fifteen document/decoder/identity tests plus actual OCR,
RPC and CLI checks. Identity keys are fixtures; no Azure authentication is proven.
The worker requests only the fixed parser audience using its explicit identity.

Parser image verification installs four exact, hash-pinned Linux wheels from the
already-qualified application dependency versions, without an Azure SDK or cloud
credential. Pip/ensurepip are removed. The new image has not yet been vulnerability
scanned. Previous image findings are retained separately and are not a clean scan.

Retained schema faults cover the image-gate resource dependency cycle, native
storage lifecycle property mismatch and deprecated container ID reference. Repairs
were made in the generator and fresh output regenerated. API61/JavaScript299 tests
pass. No medium case, native account plan, full28 acceptance or deployment is claimed.
