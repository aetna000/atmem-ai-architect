# Hosted control plane — implementation in progress

This is a separate authenticated control plane for the planned Google-hosted
Architect. It is **not** a hosted replacement for the complete local app yet.
No cloud resource or production payment was created by the implementation tests.
Project ownership/artifact storage, model execution/budget admission, isolated
generation/test workers and account export/deletion remain required launch work.

Implemented contracts:

- Server-verified Firebase Google identity, revocation checks and exact owner
  billing administration. No local bootstrap token, client-selected UID or grant.
- USD micro-unit ledger, one-time welcome grants, atomic credit reservations,
  receipt-bound settlement, uncertain-request retention, idempotent payments and
  cumulative refunds. Concurrent requests cannot overspend an admitted balance.
- Real Firestore transactions, with explicit project/database and no memory fallback.
- Stripe Checkout with server-owned amount/order snapshots, stable idempotency,
  exact raw-body webhook verification and authoritative payment/line-item checks.
- AES-256-GCM BYOK storage bound to UID/provider, versioned encryption keys,
  revision-checked edits/removal and no plaintext key response. Storage does not
  establish model permissions or provider acceptance.
- Bounded account APIs, shared per-UID rate counters, no-store responses and
  request errors that never echo submitted provider keys.

## Local verification

```sh
uv venv --python 3.13 .hosted-venv
uv pip install --python .hosted-venv/bin/python --require-hashes -r hosted/requirements.lock
.hosted-venv/bin/python -m unittest discover -s hosted/tests -v
```

Without an explicit emulator the three Firestore integration tests skip. Run
actual persistence/concurrency tests locally with Java21, Node22 and Firebase CLI:

```sh
npx --yes firebase-tools@15.18.0 emulators:exec \
  --project demo-architect-hosted --only firestore --config hosted/firebase.emulator.json \
  '.hosted-venv/bin/python -m unittest discover -s hosted/tests -v'
```

The emulator uses synthetic data only. This proves local Firestore behavior,
not IAM, live Firebase identity, a deployed database or cloud scale.

## Explicit service configuration

Run `uvicorn hosted.api:configured_app --factory --host 0.0.0.0 --port 8080`
only inside the reviewed hosted service. Supply:

| Variable | Contract |
| --- | --- |
| `ARCHITECT_GOOGLE_PROJECT` | Explicit authorized Google project; no default discovery. |
| `ARCHITECT_FIRESTORE_DATABASE` | Explicit dedicated reviewed database. |
| `ARCHITECT_DATA_ENVIRONMENT` | `sandbox` or `production`; different collection namespaces. |
| `ARCHITECT_STRIPE_MODE` | `disabled` (default), `test` for sandbox, or `live` for production. |
| `STRIPE_SECRET_KEY` | Mounted Stripe secret for the selected mode. Never source control or browser code. |
| `STRIPE_WEBHOOK_SECRET` | Mounted secret for this exact endpoint. |
| `ARCHITECT_STRIPE_ICON_FILE` | Stripe `business_icon` file ID of the existing AtMem brain artwork. |
| `ARCHITECT_CHECKOUT_RETURN_URL` | Fixed HTTPS account return page, never client input. |
| `ARCHITECT_BYOK_KEYRING` | Mounted JSON secret with `activeKey` and a `keys` map of base64 32-byte keys. |

Missing payment/vault configuration disables those capabilities; no insecure
fallback is generated. Sandbox wallets must never become real-spending wallets.
Platform spending defaults off with a zero daily budget. The model broker must
implement atomic global-budget admission before this flag can enable real usage.

The account/policy frontend is prepared in the private website repository. Keep
its enabled flag false until Google identity, CSP/rewrite, lifecycle, providers,
workers, policies and end-to-end acceptance are qualified. AtMem Cloud's ChatGPT
memory terms are a separate service and do not cover Architect credit purchases.

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
