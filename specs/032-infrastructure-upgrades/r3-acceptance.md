# R3 actual GitHub acceptance — proposed, not yet authorized

The local browser/API and isolated Terraform tests do not establish GitHub acceptance.
T016 remains incomplete until the actual remote scenarios below have evidence.

## Exact disposable scope

Owner: `aetna000`. Four **new private** repositories only:

- `aetna000/atmem-maintenance-r3-module`
- `aetna000/atmem-maintenance-r3-consumer-a`
- `aetna000/atmem-maintenance-r3-consumer-b`
- `aetna000/atmem-maintenance-r3-unprotected`

[evidence/r3-acceptance-scope.json](evidence/r3-acceptance-scope.json) contains the exact
seed files, file digests, repository mapping, allowed actions and overall scope digest.
The unrelated fourth repository is a negative control, never an upgrade target.
Existing customer/application repositories are excluded.

Creating the repositories, inserting initial fixture files, operator merges/tags,
protection setup and injected human commits are acceptance-operator operations.
They are not product capabilities. The module fixture has one echo-only workflow;
GitHub Actions may execute and bill after a push or PR. No cloud credentials or
cloud deployments are involved. Cleanup/deletion is separately confirmed.

## Credentials

Use the interactive `scripts/maintenance-github.py --home <private-home>` to connect
project `r3-disposable-acceptance` to exactly these four repositories. Use a short-lived
fine-grained token for this resource owner, selected repositories only, metadata read,
contents read/write and pull requests read/write. No workflow, merge, release or
administration capability is requested by the product broker. Keep the token in the
OS keychain; never pass it in arguments or put it in the manifest. Operator setup may
need different owner permissions; those do not enter the product's credential path.

## Staged driver

`scripts/maintenance-github-acceptance.py` defaults to `plan`: local fixture loading,
no keychain access, network calls or remote writes. It uses the existing qualified
worker configuration without rebuilding or changing that worker.

1. Review `plan`. Separately authorize the disposable scope and fixture setup.
2. Create/seed the exact private fixtures and initial module tag `v1.0.0` as operator.
3. `prepare --home ... --worker-config ... --connection ... --approved-scope ...`
   verifies exact current seed bytes, fetches immutable sources and runs real isolated
   module/control/consumer checks. Evidence remains private under the chosen home.
4. `preview` with the same arguments saves the exact module-wave preview. Inspect
   every repository, file, patch, base, ref and automation disclosure.
5. `publish ... --confirm-preview <reviewed-preview-digest>` grants that wave only.
   `status` reads bounded remote observations; `reconcile` records observable writes
   without dispatching a new mutation. Restarting never implies permission to publish.
6. As acceptance operator, merge the disposable module proposal and create its actual
   release tag. `observe-release ... --tag <existing-tag>` fetches actual bytes, checks
   equality and reruns consumers against the immutable released commit.
7. `preview` now prepares the consumer wave. Review it and supply its new digest to
   `publish`. The module-wave confirmation cannot publish consumers.
8. Exercise partial consumer merges, stale receipts and renewed remaining-wave checks.

Every non-plan command requires the exact approved scope digest. Publication additionally
requires the exact current preview digest. Driver preparation and syntax checks alone
are not proof that its live path works.

## Mandatory actual remote scenarios

| Scenario | Required observation |
|---|---|
| Module and two consumers | Actual related draft PRs; consumer source pins independently fetched release SHA |
| Default/unprotected repository denial | Broker refuses default/tag/unowned updates even without GitHub protection |
| Protected proposal branch | Provider rejects unauthorized branch changes; no bypass or fallback force push |
| Timeout after accepted ref/PR write | Restart/reconcile finds the original; no duplicate PR or blind uncertain retry |
| Lost response with no observable PR | Needs attention; no new publication merely because a response is missing |
| Conditional checked refresh | New checked delta appends with expected-head CAS; no force push |
| Human commit race | Human commit survives; stale authorizations fail |
| Competing installation | Ownership anchor prevents a foreign coordinator adopting the campaign |
| Revocation/expiry | New intents stop; accepted in-flight effects remain visible for reconciliation |
| Source/tag drift | Current checks/authorization invalidate; mismatching release bytes cannot pass |
| Partial merges | Remaining consumers lose old evidence and need checks plus a new exact confirmation |
| Imported project | Useful historical evidence retained; credentials/grants/private release proof not restored |

Record exact tool/code/recipe identities, actual API outcomes, timestamps, PR URLs and
redacted request/fault boundaries in `evidence/r3.json`. Do not store tokens or private
source in public evidence. The driver covers the staged normal path; fault/protection,
revocation and human-race controls still need operator setup and actual evidence.

T017 follows T016. Hosted R4 additionally requires explicit governance alignment;
no Cloud VM restart or hosted rollout is part of this acceptance request.
