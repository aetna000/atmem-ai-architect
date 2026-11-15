# Firebase-first hosted Architect pilot — implementation in progress

This is a separate X-only authenticated control plane, not the complete hosted local app. The owner selected Firebase services first, with Google Cloud for worker compute and OpenRouter for models. [Current plan](../specs/031-hosted-google-platform/plan.md) records requirements, actual configuration and outstanding launch work.

## Active pilot

- Firebase Hosting serves the site; Firebase Authentication handles Twitter/X sign-in. Server-side whitelist records in Firestore authorize each operation. Other existing website sign-in providers remain untouched and cannot authorize this pilot.
- The administrator is @atmemai, but privileges require its verified numeric X ID in operator configuration. No first-signup admin, handle matching or browser-supplied role.
- Firestore owns profiles, access, audited settings, integer USD credits and transactional project metadata. Every admitted X identity receives USD20 once, even if its Firebase UID is recreated.
- Cloud Storage for Firebase holds immutable project bytes. Saves use 256 KiB chunks, SHA256 checks and a 64 MiB project limit; users can save/download/remove only their projects. The API never accepts client object names or bucket selection.
- OpenRouter is the managed model provider and the only BYOK connection in this pilot. Keys are encrypted and tenant-bound; plaintext is never returned. BYOK provider billing and managed wallet usage remain separate.
- Sol Medium is preselected. Administrators may choose from the live OpenRouter catalog, with Sol Medium and Terra Medium presets; model choice is server-owned.
- Stripe credit purchases are TODO. The pilot has no checkout or payment-webhook routes. Historical billing modules below remain inactive and are not the pilot entry point.
- The account-only Cloud Run API is deployed and exercised with real Firebase X login and private project storage. AtBots generation workers remain undeployed. Managed spending remains off pending the broker and budget/worker qualification.

## Runtime configuration

Use `uvicorn hosted.pilot_api:configured_pilot_app --factory --host 0.0.0.0 --port 8080` only in a reviewed deployment. Do not launch `hosted.api:configured_app`, which is the superseded Google/Stripe preview.

| Variable | Contract |
| --- | --- |
| `ARCHITECT_GOOGLE_PROJECT` | Explicit Firebase/Google project. |
| `ARCHITECT_FIRESTORE_DATABASE` | Explicit reviewed database; separate from the existing ChatGPT service. |
| `ARCHITECT_DATA_ENVIRONMENT` | Required `sandbox` or `production`; disjoint pilot collection and object prefixes. Production rejects emulator endpoints. |
| `ARCHITECT_FIREBASE_STORAGE_BUCKET` | Explicit reviewed Firebase Storage bucket; service identity has only required object permissions. |
| `ARCHITECT_ADMIN_X_IDS` | Comma-separated verified immutable numeric X IDs; required, no default or public bootstrap. |
| `ARCHITECT_ALLOWED_X_IDS` | Optional initial numeric IDs. Persisted whitelist revocation overrides initial allow entries. |
| `ARCHITECT_STRIPE_MODE` | Must remain `disabled` for this pilot. |
| `ARCHITECT_BYOK_KEYRING` | Mounted JSON secret: `activeKey` and `keys` map of base64 32-byte encryption keys. Missing secret disables key storage. |

Firebase Storage and Firestore browser access to server-owned pilot data must be denied. Server SDKs use IAM, so rules alone do not isolate the API. Do not deploy blanket rules over existing site datasets. Review bucket generation, staging expiry, retired-object lifecycle, recovery and IAM before enabling saves in production. Storage prefixes are namespace separation, not an IAM guarantee. Durable retirement/orphan reconciliation and expired-upload cleanup remain open.

Project completion currently assembles at most 64 MiB in memory, plus JSON processing overhead. Choose bounded request concurrency and adequate memory in the reviewed deployment. Metadata deletion immediately denies application downloads; physical object removal follows lifecycle and cannot be described as immediate deletion.

## Verification

```sh
uv venv --python 3.13 .hosted-venv
uv pip install --python .hosted-venv/bin/python --require-hashes -r hosted/requirements.lock
npx --yes firebase-tools@15.18.0 emulators:exec \
  --project demo-architect-hosted --only firestore --config hosted/firebase.emulator.json \
  '.hosted-venv/bin/python -m unittest discover -s hosted/tests -v'
```

Current full local suite: 60 tests passed with no skips. Firestore tests use the actual local emulator and synthetic demo project. Object payload tests use an explicitly named fixture. Separate real X/cloud-account checks now qualify login, profiles and project roundtrips; see the deployment evidence. Model execution remains unqualified. Running without the emulator skips six integration checks.

AtBots uses a separate environment because its AtMem dependency and Firebase Admin require incompatible cryptography versions:

```sh
uv venv --python 3.13 .worker-venv
uv pip install --python .worker-venv/bin/python --require-hashes -r hosted/worker-requirements.lock
```

AtBots 0.3.1 is pinned. The local native-provider smoke check used a Pydantic test model, not a real model request or VM. The shared API must not execute untrusted project checks or share provider credentials across users. Full job admission, worker isolation, durable progress, usage reconciliation and account export/deletion are still required.

## Historical payment work — deferred

The following describes prior sandbox evidence, not currently enabled payment functionality.

## Stripe acceptance and branding

SDK17.0.0 / API `2026-10-28.endive` is pinned. The current API accepts
`allowed_payment_method_types`; the retired `payment_method_types` request was
caught and corrected by a real sandbox request.

The operator-only test harness requires an explicitly approved Stripe CLI account
and the local emulator. It uses **only** the test key, a real Stripe CLI signing
secret and a loopback webhook receiver. It creates one unpaid USD1.37 checkout;
complete it with an official Stripe test card. It then checks payment, duplicate
fulfillment and a real USD0.37 sandbox refund via signed webhooks:

```sh
FIRESTORE_EMULATOR_HOST=127.0.0.1:8897 .hosted-venv/bin/python \
  -m hosted.tests.stripe_checkout_testmode \
  --account YOUR_APPROVED_STRIPE_TEST_ACCOUNT \
  --state-file /tmp/architect-stripe-test-state.json
```

Never paste credentials into chat or issue bodies. The state file contains test
references/checkout URL, not API keys; private CLI signing logs are deleted.
The return page is not deployed by this test and may return404 until website
publication. That is not a successful deployed-user-journey claim.

Per-session checkout settings pin the full AtMem AI Architect name, approved
rose/pink colors and server-configured brain icon. Exact creation parameters are
retained with the order so a subsequent branding deployment cannot change a
retry under the same provider idempotency key. Terms/privacy links target
`https://atmem.ai/terms` and `https://atmem.ai/ai-architect/privacy/`; these pages
must be published and checked before any public checkout opens.

Account-wide branding, receipt/statement names and Stripe's account-wide footer
links also need authenticated account-management access. A usable sandbox key
does not grant that access. No account/bank/tax/payout changes are part of the
payment test. Dispute freezes/reconciliation, user
refund admission, recovery scanning and retention are still launch requirements.

Primary references reviewed15 November2026:
[Stripe fulfillment](https://docs.stripe.com/checkout/fulfillment.md?ui=full-page),
[Stripe webhook signatures](https://docs.stripe.com/events/manage-webhook-endpoints#signature-errors),
[Checkout parameters](https://docs.stripe.com/api/checkout/sessions/create),
[Stripe test cards](https://docs.stripe.com/testing),
[Firebase token verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens),
[Firestore transactions](https://firebase.google.com/docs/firestore/manage-data/transactions),
[OpenAI key handling](https://developers.openai.com/api/reference/overview).
