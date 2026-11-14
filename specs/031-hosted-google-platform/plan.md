# Public Google-hosted Architect

Owner direction, 2026-11-15: host Architect using the existing atmem.ai Firebase/Google project; anyone may sign up; grant a configurable initial credit amount; sell AI credits through Architect; use a platform OpenRouter connection or a user's Anthropic/OpenAI API key; retain a path to scaling.

## Observed existing state

- Website source is private `javadtaghia/atmemai-platform`, under local `gitlab/atmemai-platform`. Its main working tree contains unrelated edits and is untouched. Website changes use isolated `atmemai-google-hosting`, from verified remote main063bcc1.
- Current site is static Firebase Hosting; the Architect workspace is a reserved placeholder, not a running backend. Firebase identity/admin specifications exist; no deployed customer wallet or payment flow is established by them.
- Authorized Google project `atmemai` is active with billing enabled. Firestore, Identity Toolkit, Cloud Run, Secret Manager and Cloud Build APIs are already enabled. Existing Firestore databases are `(default)` in nam5 and `atmem-chatgpt` in us-central1. No resources have been created or modified for this task.
- The released local app has a shared loopback bootstrap token and local-owner filesystem scope. It must not be exposed as a public multi-user service unchanged.

## Architecture and boundaries

1. Firebase Hosting/CDN serves the Architect frontend independently from marketing pages. Reuse Firebase Authentication with server-verified issuer, audience, expiry and verified identity. Preserve the site's existing Google sign-in decision initially. Public registration is distinct from authorization to spend credits or run work.
2. A stateless Cloud Run control API owns account registration, project ownership, credit reservations, payment events, model routing and job admission. Never trust browser-supplied UID, price, balance, grant, role or entitlement.
3. Durable transactional storage owns balances, append-only ledger entries, one-time welcome grants, checkout receipts, usage reservations, idempotency and job leases. Storage adapters must support atomic cross-record updates; process-local locks are not a distributed concurrency guarantee.
4. Object storage holds versioned tenant/project documents and immutable artifacts. No authoritative SQLite/project files on Cloud Run's ephemeral filesystem. Keep existing waitlist/admin and ChatGPT datasets separate.
5. A model broker supports platform-funded OpenRouter requests and separately scoped user-owned Anthropic/OpenAI keys. Credentials stay encrypted server-side, never in public configuration, logs, browser persistence or generated projects. BYOK provider charges are distinct from AtMem-funded model usage. Compute/fair-use limits apply to both.
6. Native generation and untrusted application checks run in separately isolated workers, not in the shared authenticated API. Scale these independently with explicit concurrency and execution budgets. Current native adapters, account isolation and tool capabilities need qualification on the chosen cloud worker; a UI/API deployment cannot claim generation/test acceptance.
7. Public signup receives exactly one welcome grant per verified account. Reserve credits atomically before platform model calls, settle recorded usage once, release only proven unconsumed reservations, and retain uncertain operations rather than blindly retrying or refunding them.
8. Payment fulfillment uses verified server/provider evidence, server-owned configurable purchase quotes and idempotent receipts. Returning from checkout never mints credits. Duplicate/out-of-order webhooks, refunds, disputes and restart recovery require tests.
9. Website claims/privacy, account deletion/export, stored regions, credential retention and billing terms must be updated before public launch. Website repository instructions require owner merge and deployment only from its validated main artifact; prepare the complete PR before requesting that final step.

## Dependency-ordered delivery

- HG-1: Evidence audit, architecture, contracts and configuration boundaries.
- HG-2: Transactional credit/account/idempotency domain with concurrency/failure tests.
- HG-3: Firebase token verification and tenant/project authorization, durable database/object adapters and actual emulator isolation tests.
- HG-4: Configurable arbitrary-amount purchases, checkout adapter, verified fulfillment, refund/dispute reconciliation and real provider test-mode evidence.
- HG-5: OpenRouter/platform usage and encrypted BYOK routing, usage admission/settlement/recovery; no model or price inferred from a name.
- HG-6: Public signup, credit balance/top-up and provider controls integrated into Architect's frontend; preserve the local mode.
- HG-7: Job/worker isolation, durable progress/artifacts and all applicable generation/check/export paths qualified.
- HG-8: Least-privilege Google infrastructure, concrete price/concurrency limits, backups, monitoring, CI and rollback. Review deployment plan and cost scope before provisioning.
- HG-9: Full user journeys and failure/abuse/security tests, private website owner-review PR, approved cloud deployment and live verification.

## Launch decisions still needed

Owner confirmed: USD5 welcome balance, USD1 minimum purchase with arbitrary larger amounts, configurable in an admin view restricted server-side to verified Google login taghia.javad@gmail.com. Stripe Checkout is selected. Credits are denominated in USD micro-units; purchase amounts use integer cents. Platform model-cost multiplier and launch spending caps remain visible operator configuration, not an implicit unlimited subsidy. Hosting region and spending/concurrency caps require concrete review; us-central1 is a proposal matching an existing regional service, not an agreed residency requirement. The earlier US$12 private VM pilot estimate does not price this public credit-funded platform. Model/provider keys and payment credentials are not yet supplied or inspected.

Plans, local/mock tests, emulator tests, provider test mode, cloud plans and deployed checks remain distinct. Do not enable public spending, payment fulfillment or native execution from placeholders.

## Implemented evidence checkpoint

See progress.json, decision-log.md and evidence/. The ledger/control-plane/vault and disabled private account preview are implemented. HG-3 through HG-9 remain incomplete: no hosted engine, model broker, project/artifact tenancy, worker isolation or cloud deployment is established. The real Stripe sandbox check does not establish production account-wide branding or a live public return page.
