# AWS scenario qualification

This is an execution journal and test procedure, not a declaration of deployment support.

## Scenarios

| ID | User outcome | Required deployed evidence |
|---|---|---|
| 01 | Private document storage | Read/write round trip, denied access, configuration checks, approved cleanup |
| 02 | Document statistics | Exact output, malformed/oversized input rejection, denied invocation, application update |
| 03 | Async processing | Upload-to-result path, safe duplicates, dead-letter handling, recovery |
| 04 | Model summary | Actual model invocation, limits, failure handling, redacted logging |
| 05 | Cited RAG | Retrieval relevance, valid citations, abstention, update/delete propagation |
| 06 | Permission-aware RAG | Cross-user isolation, no metadata leakage, revocation, fail-closed identity/region |
| 07 | External sources/channels | Approved source sync, deletes/ACL changes, outage recovery, authenticated channel |

The catalog is `src/aws-validation-scenarios.mjs`. Synthetic fixtures do not become customer requirements or approved cloud configurations.

## Live baseline

`node scripts/aws-scenario-live.mjs 01-private-storage` starts isolated app services and uses the normal chat and download UI with a signed-in native model client. `all` runs the seven scenarios sequentially. Set `ATMEM_ARCHITECT_VALIDATION_PROVIDER` to an available client if required. This is opt-in real model usage; it does not provision AWS resources.

Each run writes under ignored `.local/aws-validation/<timestamp>/`: input prompt, actual model response, workspace, screenshot, downloaded delivery pack, extracted Terraform and handoff records, and validation stages. The browser uses real app/model endpoints, not mocked responses. Test memory is isolated from the user's normal workbench store.

Architecture assertions are mechanical checks (required service families, scope, connections and preservation of existing sources). They do not prove regional availability, correctness, security or deployment. Unsupported generated infrastructure remains blocked. AWS plans, applies, application tests and cleanup have separate stages.

## Initial findings

- Rechecking aetnamem/.env.atmem-c709e confirmed AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are present. This supersedes the earlier no-AWS-variables observation. No credential values are copied into tests or reports. Region and spending limit remain unspecified.
- The initial browser harness submitted before session readiness; that attempt was recorded as a harness failure. The corrected runner waits for the app's connected indicator.
- Native infrastructure generation beyond S3 is not yet complete. Real scenario results will determine the next product corrections; no manual patch to an exported artifact counts as generator success.
- AWS provisioning is pending an agreed account/profile, region, spend envelope and concrete resource plan.

## Execution policy

Complete generation and local checks before presenting the account-specific resource plan. Record source/configuration identity and approvals; do not apply an outdated plan. Use synthetic documents and isolated test resources. Reconcile actual outcomes and leftovers; deletion/cleanup must stay inside the agreed test scope. Stop expansion when a simpler stage fails, fix the product, then rerun that stage.


## Corrections from the first live runs

The private-storage model response described bucket-owner enforcement and HTTPS access, while native generation only included encryption/versioning/public-access blocking. The generator now emits ownership controls and a deny-insecure-transport bucket policy, plus bucket-name/ARN outputs for verification. The transport policy follows [AWS condition-key guidance](https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html), excluding AWS service principals from that deny.

The compute, summarization and permission-aware scenarios initially drew caller/response payloads as proposed non-AWS components. Architect guidance now separates external actors, physical services and application response responsibilities; affected scenarios are rerun through the real UI. This is a prompt correction with observed regression runs, not a claim that all model outputs will always comply.

`scripts/aws-artifact-check.mjs <run-directory>` records configuration-load and provider-schema checks separately. A missing provider stays blocked. `scripts/aws-storage-verify.py` is an explicit opt-in verifier for an agreed test bucket; it checks account/region, configuration, two synthetic versioned writes/readbacks and anonymous denial, then deletes only its own created versions. It journals the object key and version IDs before/after writes so interruption does not hide cleanup work. It does not destroy infrastructure. Local mock tests are not proof that this verifier has passed on AWS.

## Recorded results — 2026-11-07

All seven real-model prompt-to-export retests passed structural architecture checks after corrections (initial baseline: 4/7). All seven Terraform configurations load; provider-schema validation remains blocked by the absent provider and insufficient disk space. No AWS operations have run.

| Scenario | Initial architecture | Latest architecture/export | Remaining generation gaps |
|---|---|---|---|
| 01-private-storage | passed | passed / passed | 2 |
| 02-document-compute | failed | passed / passed | 7 |
| 03-async-documents | passed | passed / passed | 12 |
| 04-model-summary | failed | passed / passed | 9 |
| 05-cited-rag | passed | passed / passed | 10 |
| 06-permission-rag | failed | passed / passed | 15 |
| 07-enterprise-connectors | passed | passed / passed | 24 |

See `aws-scenario-validation-results.json` for evidence paths and artifact hashes. Passing structural checks is not deployment readiness. Native implementations beyond S3 and unresolved integrations still require work.

## AWS access preflight

The user subsequently authorized Australia and a $20 total test envelope, with US fallback for model services. Sydney is selected for the initial tests; price superiority is not established. Currency remains unspecified, with AUD used as a conservative planning assumption. Read-only STS verified the supplied credentials. Bedrock reports Nova Micro and Nova Lite authorized and available in `ap-southeast-2`, `us-east-1` and `us-west-2`. No model inference or provisioning occurred. Evidence: `.local/aws-validation/aws-access-preflight.json`. These results supersede the earlier pending-access status.

Disk space subsequently became sufficient to install the signed AWS provider 6.72.0. All seven latest exports now pass `terraform validate` against that provider, superseding the earlier schema blocker. This validates the emitted configuration only; missing infrastructure and integration gates still block deployment.

## Product correction loop

`node scripts/aws-scenario-live.mjs all 2` runs an original prompt and a findings-driven refinement in the same browser conversation for each scenario. It records both rounds, diagrams, responses and exports. `node scripts/aws-artifact-check.mjs <run>` validates the exact extracted files, then `node scripts/aws-loop-report.mjs <run>` summarizes candidate blockers and whether implementation gaps changed. The runner never deploys.

Candidate evaluation now rejects disconnected graphs, misleading labels when an explicit service conflicts, empty AWS resource sets, missing required native resources and unresolved implementation gates. Provider-schema validation, application acceptance and requirements review are independent. No numerical success likelihood is claimed. Missing native implementation remains product code work even if the model produces a better explanation.

## Qualification cycle findings

The two-round live run `.local/aws-validation/2026-11-07T04-14-28.074Z` produced 14 exports, all passing architecture structural checks and installed-provider schema checks. All seven deployment candidates remain blocked. In scenarios 1–5 the implementation gaps did not change through conversation; scenarios 6–7 expanded their designs and require review, not an automatic improvement claim.

Product defects reproduced and corrected:
- RAG workflow selection previously triggered on documents/files alone, including storage-only requests. It now requires retrieval/question-answering intent.
- Combined CloudTrail/CloudWatch and Bedrock model/guardrail service fields could lose a physical dependency during resource resolution. They now remain explicitly ambiguous.
- Skill version reporting was hardcoded. It now reflects the reviewed file version.
- Structural validation accepted misleading service labels and disconnected subgraphs; candidate evaluation now preserves implementation and missing-evidence blockers even when Terraform validates.
- An expanded AWS skill exceeded the 1,900-character memory publication boundary. Its first retest failed before model invocation; the guidance was shortened and publication-boundary regression coverage added. Failed run: `.local/aws-validation/2026-11-07T04-21-24.289Z`.

After AWS guidance correction, the async retest explicitly specifies exact-version reads with `s3:GetObjectVersion`, SQS visibility at least six times the function timeout plus batching window, and partial-batch failure handling. These are observed design improvements, not implemented runtime evidence. Sources: [S3 GetObject permissions](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html), [Lambda SQS configuration](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html).

The next implementation work is a typed operator identity/access contract for the S3 scenario, followed by native Lambda/IAM/logging and application artifact generation for scenario 2. Additional prompt rounds cannot implement these modules. Keep deployment blocked until generated artifacts satisfy the scenario, review, local tests and account-plan checks.

The final three-scenario retest passed prompt, structural architecture, export and provider-schema checks. Storage uses the general architecture skill; async version-reading guidance is reflected in the diagram; the permission-aware retest separates model invocation from guardrails. All remain blocked deployment candidates. This cycle produced 17 schema-validated exports; current tests: 143 JavaScript, 63 server, browser suites and build passed. See `aws-qualification-loop-results.json` for retained failures, corrections and exact artifact hashes. No AWS calls occurred during this correction cycle.

## Native implementation qualification, 2026-11-07

The generator now emits typed storage access, text-statistics Lambda, S3/SQS/Lambda/DynamoDB word-count processing, and Bedrock summary handlers. Each includes source, deterministic packaging where required, application tests, scoped permissions, review gates and mock-provider tests. Unsupported architectures still remain blocked.

The frozen-source browser run `.local/aws-validation/2026-11-07T05-09-01.613Z` passed two prompt/export rounds each for async processing and summaries. Both downloaded async exports passed six packaged application tests; both summary exports passed four. All four exports passed provider initialization/schema and four shipped mock plans. These are local implementation checks, not deployed results.

The async fixture `.local/compute-validation/2026-11-07T05-05-32.459Z` passed a read-only Sydney account plan. A subsequent read-only preflight found the account's Lambda concurrency quota is 10, leaving no capacity for the required positive function reservations. `.local/account-preflight/async-account-preflight.json` records that blocked prerequisite. A successful Terraform plan did not discover it. Generated exports now include `preflight-aws.py` and `PREFLIGHT.md` to check account identity, quota capacity and selected Bedrock control-plane availability before apply. Runtime availability remains separate.

The earlier run `.local/aws-validation/2026-11-07T05-04-53.187Z` retained a failed second round: development hot reload interrupted the browser response. The harness now snapshots source for the whole run, and the subsequent two-round tests passed. Do not erase that failure or count it as model success.

No resources were provisioned and no Bedrock inference was performed in this qualification cycle. Live acceptance, recovery and cleanup remain outstanding.

## First live AWS storage qualification

The real prompt-derived storage project was rendered through the compiler with explicit `qualification` lifecycle and deployed in Sydney. The run `.local/live-storage/6f875fc797e9` passed scoped-role uploads, byte-preserving reads using both returned version IDs, listing, authenticated deletion denial, anonymous read denial and bucket hardening checks. The scoped role had no attached or inline identity policies; access came from the generated bucket policy. A post-test refresh plan had zero changes. Created object versions, all Terraform resources and the temporary IAM role were removed successfully. `receipt.json` records events and exact artifact digests.

This establishes one bounded live storage scenario, not overall production readiness. Staging/production destruction protection remains intact; qualification explicitly permits cleanup while `force_destroy` remains false. Broader recovery/update tests remain separate.

AWS accepted the user-authorized Sydney Lambda concurrency request of 1,001 and opened a support case. The actual Lambda quota remains 10 as last checked; account preflight blocks compute applies without removing the generated per-function limits. No Lambda deployment or model inference has occurred yet.
