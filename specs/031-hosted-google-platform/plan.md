# Firebase-first hosted Architect pilot

Current owner direction, 2026-11-15, supersedes the earlier public Google-signup and payment launch proposal. Preserve historical Stripe sandbox evidence; Stripe purchases are now TODO.

Canonical hosted URL: **https://atmem.ai/architect**. Early access is invite only; request access by DM to @AtMemAi on X or email javad@atmem.ai. Preserve existing local documentation URLs.

## Accepted scope

- Existing `atmem.ai` Firebase/Google project; use Firebase services wherever they fit, then Google Cloud for remaining compute.
- X is only the application's identity provider. Access requires a server-owned whitelist. Administrator: `@atmemai`, pinned to its verified immutable numeric X ID before activation.
- Each admitted X account receives USD20 welcome credit once, an individual profile, private saved projects and project downloads.
- Managed OpenRouter is the default AI connection. Users may instead supply their own OpenRouter key and pay that provider directly. BYOK must not consume managed welcome credit.
- Default model: `openai/gpt-6.1-sol`, medium reasoning. Only administrators select models from the live OpenRouter catalog, including Sol Medium and Terra Medium presets. No ordinary-user model selection is required.
- AtBots runs in an isolated Google Cloud worker VM. Managed access uses OpenRouter, not the owner's ChatGPT subscription.
- Stripe credit purchasing remains deferred. Do not expose checkout, purchase fulfillment or Stripe account management in the pilot.

## Service allocation and boundaries

| Responsibility | Selected service | Contract |
| --- | --- | --- |
| Public site and application assets | Firebase Hosting | Preserve existing site; same-origin API rewrite only after qualification. |
| X sign-in | Firebase Authentication, Twitter/X provider | Server verifies signed Firebase tokens and revocation; X subject comes from verified provider identity. No X content features. |
| Profiles, whitelist and administration | Cloud Firestore | Server-only access, immutable X identity, revision-aware changes and audited role edits. Handles never establish privileges. |
| Welcome grants, reservations and usage records | Cloud Firestore transactions | Integer USD micro-units; grant once per X ID, atomic admission and receipt-bound settlement. |
| Project snapshots and generated artifacts | Cloud Storage for Firebase | Server-authorized tenant ownership, immutable generations, bounded chunk uploads, integrity checks and lifecycle controls. Large payloads do not go into Firestore documents. |
| API hosting | Google Cloud Run, behind Firebase Hosting | Proposed stateless Python service; preserves current Python engine and permits independent scaling. No publicly exposed local sidecar. |
| Generation and checks | Google Compute Engine VM with AtBots | Separate worker runtime and least-privilege service identity. Durable job metadata in Firestore; private project execution and explicit resource budgets remain required. |
| Operator/model and encryption secrets | Google Secret Manager | Server-only scoped secrets; encrypted user OpenRouter credentials in Firestore. Never put provider keys in projects, UI responses or logs. |
| Model catalog and inference | OpenRouter | Administrators own model policy. Live catalog validation, medium reasoning, atomic budgets and actual usage settlement. |
| Future purchases | Stripe, TODO | Disabled until separately qualified and enabled. |

Firebase Authentication establishes identity; Firestore whitelist records establish application access. Every application operation rechecks access. Authentication through another product's Google provider cannot authorize Architect. Preserve existing site authentication providers, administrator roles and ChatGPT datasets.

The API uses `architect_pilot_sandbox` and `architect_pilot_production` Firestore collection namespaces and matching object prefixes. Neither shares the earlier Google/Stripe wallet namespace. Production rejects Firebase emulator configuration. SQLite is only a local test adapter, never a production fallback. Final deployment must review a dedicated database/bucket and IAM boundaries; namespaces alone are not IAM isolation.

## Dependency-ordered delivery

- HG-1: Evidence, owner decisions, Firebase-first contracts and configuration boundaries.
- HG-2: Transactional credit/idempotency domain and failure/concurrency evidence.
- HG-3: X identity, immutable administrator bootstrap, Firestore whitelist/profiles and Firebase Storage project ownership. Actual emulator checks plus real OAuth and storage IAM acceptance.
- HG-4: Deferred Stripe work; preserve historical sandbox evidence. Not a pilot launch dependency.
- HG-5: OpenRouter catalog/admin policy, encrypted BYOK, exclusive request dispatch, atomic daily-budget/credit admission and usage reconciliation.
- HG-6: X-only account/project frontend and administrator controls; USD20 balance, managed/own OpenRouter connection, no checkout. Preserve local mode.
- HG-7: AtBots worker VM, durable jobs/leases/progress, isolated generation/checks and all applicable export paths.
- HG-8: Concrete region/cost plan, least-privilege Google resources, backups, lifecycle, monitoring, CI and rollback. Review actual provisioning/cost scope before creating runtime resources.
- HG-9: Complete admission/save/generate/check/download/revocation journeys; owner-reviewed private site PR and validated-main publication, then live verification.

## Observed configuration and evidence

Firebase's Twitter provider is configured and enabled using the separate AtMem AI Architect X app. Callback: `https://atmemai.firebaseapp.com/__/auth/handler`. X has read permission, no email request, and no content integration is implemented. Existing X apps and Firebase identity providers were preserved. The generated OAuth2 credential pair was saved privately in Secret Manager; Firebase uses the separately configured OAuth1 consumer credentials. AtMem.ai and localhost were added to authorized domains while preserving existing domains. No secrets are retained in these specifications.

The actual numeric ID of `@atmemai` has not yet been verified by a real Firebase X sign-in; do not derive it from the developer console account URL. The application stays disabled pending that acceptance and full backend/worker qualification.

The local Firestore emulator suite currently passes 60 tests with no skips. This includes real Firestore pilot signup/grant concurrency, durable whitelist revocation, project metadata commit/cancel/delete, and environment separation. Object payload tests use a named storage fixture, not cloud storage. Native AtBots 0.3.1 was installed in a separate local worker environment and its native provider exercised with a Pydantic test model; no VM installation or live managed model request is established.

## Remaining launch boundaries

Storage/processing region, lifecycle and account deletion/export, daily spending and worker concurrency require concrete qualification. The object adapter still needs durable retirement/orphan reconciliation and expired-upload cleanup. The API currently assembles project uploads in bounded memory (64 MiB/file), requiring a reviewed deployment memory/concurrency limit. No cloud VM, hosted model broker or complete generation service is running from this work. Platform spending remains off. A successful emulator, OAuth configuration or sandbox payment does not establish deployment.

Website changes use the isolated private `atmemai-google-hosting` branch. The owner alone merges that repository; publication uses only its checksum-verified validated main artifact. Keep its signup flag false until full acceptance.
