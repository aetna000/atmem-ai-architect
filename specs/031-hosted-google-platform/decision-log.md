# Hosted platform decisions

2026-11-15 — Owner approved public Google signup, USD5 welcome grant once per verified account, arbitrary purchases from USD1, configurable billing restricted to verified Google login taghia.javad@gmail.com, platform OpenRouter or user-owned OpenAI/Anthropic keys, and Google/Firebase hosting with independent scaling.

2026-11-15 — Owner chose Stripe Checkout, then explicitly approved sandbox testing and renewed the CLI login. A real USD1.37 sandbox payment, duplicate fulfillment and USD0.37 refund were verified through real signed Stripe CLI webhooks against synthetic local Firestore records. No real funds moved or cloud resource was created.

2026-11-15 — Owner directed complete replacement of Deegitals branding and URLs with AtMem.ai / AtMem AI Architect. Owner supplied AtMem.ai as the service name and chose refunds for unused purchased credits. Legal entity, storage region, retention and hard operating budgets were not invented. Per-session name, brain icon and rose colors were tested. Account-wide updates require live account access; the CLI live credential was rejected, so no account-wide business/bank/tax/payout setting changed.

2026-11-15 — Sandbox wallets have a different storage namespace and cannot be paired with live Stripe mode. Retain exact Checkout request parameters before transmission, so branding/configuration deployments cannot alter retries under a prior idempotency key. Keep provider plaintext out of validation errors and UI responses.

2026-11-15 — Website changes stay in an isolated private owner-review branch. Policies are preview-labelled and signup remains disabled. Website AGENTS.md prohibits agent merges and feature-branch deployments; publish the owner's validated main artifact and verify replacement policy URLs before using them publicly.

2026-11-15 — Owner replaced public Google signup with an X-only whitelist pilot; administrator is @atmemai. Bootstrap requires its verified numeric X ID. X is solely login, not a content or model service. Existing Firebase providers and site roles remain intact.

2026-11-15 — Owner selected managed OpenRouter with USD20 welcome credit once per admitted X identity, optional user OpenRouter keys, Sol Medium default and administrator catalog selection including Terra Medium. Stripe purchases are TODO. The earlier Google/$5/payment launch scope is superseded, while its test evidence is retained.

2026-11-15 — Owner directed Firebase wherever possible, then Google Cloud. Production metadata/credits use Firestore; payloads use Firebase Storage; Hosting and Firebase Auth serve the browser. Cloud Run control API and an isolated Google VM/AtBots worker are the proposed compute boundary. SQLite is a local test adapter only. Sandbox/production namespaces and object prefixes are disjoint.

2026-11-15 — A separate AtMem AI Architect X application was created and its OAuth1 credentials configured in Firebase. Provider activation and app-key matching were verified; temporary OAuth1 credential files were deleted. Web/confidential settings use the Firebase callback, AtMem website/privacy, read permission and no email request. Generated OAuth2 credentials are in Secret Manager with no added IAM grants. Authorized domains preserve the existing Firebase domains and add atmem.ai/localhost. No VM or live AI request was created.

2026-11-15 — API and AtBots workers need separate dependency environments: Firebase Admin requires cryptography >=50.0.2; AtMem 2.3.14 requires <49. Local worker pins AtBots 0.3.1 and cryptography 48.0.1, while API pins 50.0.2. Do not weaken either dependency contract or imply a shared production environment was qualified.

2026-11-15 — Owner selected atmem.ai/architect as the hosted entry point, invite-only early access via X DM or javad@atmem.ai, matching website/docs and an intro video with background music.
