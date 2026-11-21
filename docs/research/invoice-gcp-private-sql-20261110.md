# Google invoice private database and background worker review

Reviewed 2026-11-10. This informs the native adapter; no cloud account was accessed.

- [Cloud SQL Auth Proxy](https://docs.cloud.google.com/sql/docs/postgres/connect-auth-proxy) authenticates access and encrypts the upstream connection. Private-IP selection is explicit and requires a VPC route. The application connects only to the same-instance loopback listener. This is a deliberately selected transport, not a fallback after native TLS verification fails.
- [PostgreSQL users and roles](https://docs.cloud.google.com/sql/docs/postgres/users) distinguishes service-account authentication markers from database privileges. API/worker IAM users receive no administrative database role. A separate operator identity intentionally has cloudsqlsuperuser for bootstrap. Runtime grants still reject unrelated inheritance, ownership and broad effective privileges.
- [Cloud Run billing settings](https://docs.cloud.google.com/run/docs/configuring/billing-settings) explains background CPU allocation. The worker explicitly retains CPU and a minimum instance. This does not guarantee uninterrupted execution; transactional intent, leases and queue recovery handle instance loss.
- The maintained [proxy release v2.27.0](https://github.com/GoogleCloudPlatform/cloud-sql-proxy/releases/tag/v2.27.0), source revision `6ddead5c3b7c25da0f4c7cadbad6b9ee601b4ffa`, is pinned by OCI digest in `src/runtime/cloud-sql-proxy-lock.json`. The local qualifier inspects the executable AMD64 manifest rather than mistaking an OCI index for runtime configuration.

Separate API, worker and parser service accounts remain mandatory. Only the worker may invoke the parser; the parser has no database proxy, VPC attachment, document/model grants or accounting secret. API admission uses native IAP and explicit staff principals; live SQL memberships independently govern business permissions.

Local native schemas/mock plans, exact application images, proxy command inspection and PostgreSQL fixtures do not prove destination IAM, private routing, upstream certificates or real model behavior. Full operator delivery, complete conversation/export admission, IBM parity and the wider 28-case evaluation remain unfinished. Model availability and scoped privacy approval are not fabricated by this review.
