# Proposed release train — stable versions, evidence first

Current npm release: 0.2.3. Version numbers below are reservations/proposals; rebase on latest stable before implementation. No alpha/beta suffixes. A gated capability may ship with an honest coverage label. Release dates and subscription prices are not approved here.

| Increment | Proposed version | Delivered outcome | Required exit / owner test |
|---|---|---|---|
| R0 engineering qualification | no public version | Frozen real breaking migration/source/tool contracts and worker threat model | Version-only change actually fails; AST/provider tooling selected; manual oracle and holdout frozen; hostile repo boundary demonstrated. Stop/replan if no meaningful non-version migration is proven. |
| R1 local migration | 0.3.0 | One supported AWS/Terraform migration prepared locally with downloadable changes and receipts | US1 passes on frozen and distinct composition; import/export and canceled/failed runs; no original edits or cloud access. Owner reproduces checks from clean environment. |
| R2 coordinated projects | 0.4.0 | Shared-module and consumer migration campaign with usable patch order | US2 exact overlays, compatibility sequence, no invented tags, simulated local operator-release equality and consumer rechecks (not real publication acceptance); cycles/unresolved/partial merge cases qualified; 30-snapshot discovery within reference budget. Owner reviews module+two-consumer patches. |
| R3 repository delivery | 0.5.0 | Explicitly approved related GitHub PRs and safe refresh/recovery | US3 real disposable-repo checks, local keychain token/polling, least privilege, duplicate/timeout/human edit/revocation, CI disclosure and actual released-artifact wave tests; prior gates pass. Owner approves first actual PR campaign. |
| R4 recurring service | 0.6.0 | Opt-in fleet discovery/preparation, holds, budgets and hosted qualified execution | US4 durability, isolation, secret egress, deletion/recovery, signed events, 30-repo schedule and private/public knowledge separation; hosted governance alignment approved; actual job-cost evidence. Owner enables one scope; publication still exact-patch confirmed. |

## Every release gate

All applicable unit/contract/browser and existing npm/server/build checks; supported matrix with exact provider/tool/recipe versions; independent positive/negative and changed-composition evidence; compatibility/export migrations; secret/license/dependency review; worker timeout/cleanup; source-bound acceptance receipts. No green total hides failed/blocked mandatory work. Package/install tests cover Linux/macOS/Windows clients; hosted execution is separately Linux-qualified. User-selected infrastructure provider does not determine model backend.

Deliver versioned artifact+commit+digest, concise manual test card, migration notes, measured limits/costs and rollback instructions. Pin previous working package/schema; rollback disables scheduling, reconciles in-flight writes and restores compatible application version; it never force-reverts customer PRs, state or data. Forward-only record migration requires backup/restore qualification. Public tags/npm publish and cloud deployment require owner authorization; no release from documentation alone.

## Commercial rollout

R1/R2 prove engineering value, R3 proves delivered proposals, R4 makes subscriptions operationally plausible. Billing/Stripe remains a separate approved workstream. Do not sell unlimited execution or verified production safety. Before charging, set measured job budgets, service/support boundaries and a supported-estate cap; USD1,000/month remains a testable commercial hypothesis.
