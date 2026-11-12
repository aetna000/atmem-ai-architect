# Typed approval-workflow HTTP boundary

`workflow_http.create_app(verify, store, account_id=..., public_origin=...,
operation_kind='draft', token_header=None)` exposes the shared durable workflow.
Bootstrap owns the account, operation policy, origin, typed store, verifier and
destination contract. Requests cannot set these or choose code to execute.
`store` must have an immutable `PayloadContract`; its persisted digest binding
and the existing PostgreSQL/Procrastinate approval mechanism remain authoritative.

The verifier receives an access token and returns its verified subject. Membership
and roles are looked up live in the owned account. Bearer authentication is the
default transport; the explicit IAP signed-header transport never falls back to
Bearer. These transports do not themselves authenticate tokens: a real native
verifier and protected destination ingress must be wired by the trusted bootstrap.
Synthetic verifiers in the acceptance tests prove wiring and denial behavior,
not Cognito/Entra/IAP/App ID or hosted tenant acceptance.

The API has the following closed request envelopes:

| Endpoint | Contract |
|---|---|
| GET /healthz | Process liveness only; no database/readiness claim |
| GET /api/session | Current membership roles; no account/role override |
| POST /api/operations | `{source: object}` and a stable Idempotency-Key;202 means durable enqueue |
| GET /api/operations | Bounded25-row listing with optional unique `before` cursor |
| GET /api/operations/{id} | Current authorized operation/result/receipt; no source/destination credentials |
| POST /api/operations/{id}/review | Exact `{revision: integer, result: object}` under typed payload and reviewer policy |
| POST /api/operations/{id}/approve | Exact `{revision: integer}`; existing account-change supervisor policy retained |

Source and result shape come from the owned declaration. No general business
semantics, source-system connector or state transitions are inferred from data.
Mutations require an exact configured Origin and application/json; duplicate JSON
fields, duplicate authority headers, nonfinite values and unknown envelope fields
fail. Bodies have a66000-byte transport limit including the envelope, a5-second
read deadline and20 admitted simultaneous mutation requests per process. The typed
payload limit remains64000 bytes. These are implementation bounds, not an SLA,
tenant quota, global rate limit or throughput guarantee. There is no clipping.

Identity/membership are checked before and after body streaming; SQL role/account
checks still govern the transaction. A revoked member cannot enqueue after upload.
Results returned to clients omit source references, destination configuration and
internal lease/approval credentials. Errors contain stable codes and no raw adapter
details. Responses disable caching and include restrictive content/security headers.

Same-key/same-input duplicate requests share one durable operation/queue record;
changed input conflicts. The API does not retry unknown effects or expose generic
role administration, migration, recovery, erasure or approval bypass endpoints.
Retention, tenancy within an account, identity enrollment and authorized reconciliation
remain explicit application/operating policies rather than inherited invoice defaults.

The helper and its tests are emitted with current application packages. Existing
invoice endpoints keep their domain-specific upload/evidence/review/retention rules.
Architecture-model selection, provider-owned bootstrap/database/identity wiring,
application-specific processors and full export/connected-system qualification
remain required before a generic application release. The current source and exact
unpacked package tests are in specs029's20261112-workflow-http evidence directory.
