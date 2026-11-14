# Hosted platform decisions

2026-11-15 — Owner approved public Google signup, USD5 welcome grant once per verified account, arbitrary purchases from USD1, configurable billing restricted to verified Google login taghia.javad@gmail.com, platform OpenRouter or user-owned OpenAI/Anthropic keys, and Google/Firebase hosting with independent scaling.

2026-11-15 — Owner chose Stripe Checkout, then explicitly approved sandbox testing and renewed the CLI login. A real USD1.37 sandbox payment, duplicate fulfillment and USD0.37 refund were verified through real signed Stripe CLI webhooks against synthetic local Firestore records. No real funds moved or cloud resource was created.

2026-11-15 — Owner directed complete replacement of Deegitals branding and URLs with AtMem.ai / AtMem AI Architect. Owner supplied AtMem.ai as the service name and chose refunds for unused purchased credits. Legal entity, storage region, retention and hard operating budgets were not invented. Per-session name, brain icon and rose colors were tested. Account-wide updates require live account access; the CLI live credential was rejected, so no account-wide business/bank/tax/payout setting changed.

2026-11-15 — Sandbox wallets have a different storage namespace and cannot be paired with live Stripe mode. Retain exact Checkout request parameters before transmission, so branding/configuration deployments cannot alter retries under a prior idempotency key. Keep provider plaintext out of validation errors and UI responses.

2026-11-15 — Website changes stay in an isolated private owner-review branch. Policies are preview-labelled and signup remains disabled. Website AGENTS.md prohibits agent merges and feature-branch deployments; publish the owner's validated main artifact and verify replacement policy URLs before using them publicly.
