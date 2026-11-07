# AWS prompt-to-deployment qualification runbook

## Scope and current stopping point

Run the seven scenarios in order, one isolated environment at a time. The current archive includes real prompt/refinement runs, downloaded artifacts, local code/schema/mock-plan checks and six successful real-account plans. Only an earlier storage revision has passed live deployment and cleanup. All six compute scenarios stopped at Lambda preflight; their live acceptance steps below have **not run**.

This is an executable local-validation runbook and a live qualification procedure. It is not evidence that unexecuted steps work. Do not mark an example production-ready from schema validity, a successful plan, local mocks or a model's explanation.

## 1. Load an example or reproduce its prompts

1. Install dependencies using the repository README; start `npm run local`. If Connections opens on first launch, choose Local patterns to inspect examples without credentials, or configure your preferred architect for prompt reproduction.
2. Open **⋯ → Open project file**, choose `<scenario>/project.atmem-ai-architect.json`, and inspect the diagram. The saved project is the selected second round, with its requirements and decisions.
3. To reproduce from an empty project, choose the same architect connection (`claude-code`, model `default` in the recorded runs). Submit `history/<run>/round-1/prompt.txt`, wait for the proposal, then submit round 2's exact prompt. The files include the full qualification suffix and actual refinement findings; do not substitute the shorter scenario description.
4. Keep **Draw as we talk** enabled or explicitly apply each proposal. Download the delivery pack and save the editable project. Model output may differ between runs; inspect required components and typed connections before proceeding.
5. Retain failed outputs and the reason for each correction. For scenario 07, the earlier run left disconnected human/deferred Teams nodes. The corrected run uses a typed browser connection and a note for the future channel, while retaining the required web application.

For automated prompt reproduction (requires a signed-in architect client; does not deploy AWS resources):

```sh
node scripts/aws-scenario-live.mjs 02-document-compute 2
# Or run all seven, two rounds each:
node scripts/aws-scenario-live.mjs all 2
```

The runner prints a `.local/aws-validation/<run>` directory. Audit those new outputs with `node scripts/aws-artifact-check.mjs <run-directory>`. Never overwrite the original archive to hide a regression.

## 2. Verify and reproduce the archived local checks

From the repository root:

```sh
node scripts/aws-example-check.mjs
# Exercise the real file-open menu and canvas in an isolated test browser:
node scripts/aws-example-browser-check.mjs
# Build runtimes, initialize providers, validate schemas, run application tests
# and Terraform mock plans for every archived selected export. No AWS credentials used.
node scripts/aws-example-check.mjs --artifacts
```

The second command copies exports to a fresh ignored `.local` folder. It needs network access for signed Terraform providers and hash-pinned Python wheels. Python/Node/Terraform versions should be recorded; original provider checks used Terraform 1.17.1 and AWS provider 6.72.0. Inspect the generated constraints; a later allowed provider version requires new validation. No downloaded provider binary is archived.

Check `artifact-validation.json` for each stage rather than relying on process exit alone. Runtime tests are local Python tests with mocked AWS/model calls. Terraform tests use a mock provider. They do not prove IAM enforcement, AWS retries, Cognito sign-in, real model behavior or recovery.

## Stateful local emulation

Before download, use **Outputs → Emulate locally** and save the artifact-bound report. To run all seven projects against the current generator, install the optional worker and run `npm run test:emulation`. See [coverage and setup](../../docs/AWS_EMULATION.md). This adds stateful service/runtime evidence; it does not replace the checks below or change their recorded deployment status.

## 3. Review account-bound inputs and preflight

Use your own disposable test account or explicitly approved account, region and existing principal. Never use the example placeholder account as a real destination. Preserve the configured function concurrency limits. Keep a separately protected expected-account JSON containing `aws_account_id`; keep AWS credentials outside the repository.

The archived six account plans selected `amazon.nova-micro-v1:0`, at most 256 output tokens and Sydney. Scenario 06 used synthetic subject mappings `alice`/`bob` and employee region `AU`. These are test choices, not organizational policy. The plan runner bound principal variables to its current credential identity for read-only planning; that cannot prove separation between Alice and Bob. Live tests require distinct fresh least-privilege identities.

After local checks, use the generated `deployment.tfvars.json.example` to review every required input. The archived `evidence/qualification-inputs.json` records nonsecret overrides, where applicable. Run the read-only account planner against the copied working export:

```sh
.venv/bin/python scripts/aws-account-plan.py \
  --export /absolute/path/to/working/terraform \
  --region ap-southeast-2 \
  --expected-account-file /private/path/expected-account.json \
  --env-file /private/path/aws.env \
  --reviewed-inputs /private/path/qualification-inputs.json \
  --confirm-reviewed-plan
```

This performs STS account verification, validates Terraform, creates a saved plan and runs generated preflight. It does not apply. A nonzero exit with `exitCode: 0` in the plan receipt and `preflight: blocked` means planning passed but deployment is blocked. Read both receipts.

Stop if there is unfinished work, missing inputs, unexpected deletes/replacements, insufficient quota or unavailable model access. The latest archived quota check has zero capacity available for additional reservations. Wait for actual increased Lambda capacity, not just an approved request. Do not remove concurrency limits to bypass it. Read generated `PREFLIGHT.md`; model control-plane availability does not prove an invocation will succeed.

## 4. Bounded live deployment procedure — pending

The current user authorized a total $20 budget (conservatively tracked as AUD), Sydney, synthetic documents, bounded retrieval and local connector contracts. That authorization is session-specific, not permission for people downloading these examples. They must authorize their own cloud work.

1. Create a new isolated working directory and unique qualification identity. Verify target account and region with STS. Record operator, date, input/configuration hashes, intended resource count and cost assumptions. Use no real employee or customer data.
2. Compile the reviewed project through AtMem's generator. Do not manually patch exported Terraform to remove gates. `qualification` mode is only for temporary tests; production/staging protection and production backend requirements remain in place. Read the generated runtime build instructions and build before planning.
3. Create a fresh plan after final inputs and builds. Review every resource and permission. Reject changes to existing systems, unexpected resource types or deletion of anything outside the isolated test. Retain the exact saved plan privately.
4. Require passing account/model/quota preflight. Apply only that saved reviewed plan. Record start/end, output inventory and failures. Do not rerun apply blindly after a partial failure; inspect the state and resource ownership first.
5. Run the scenario-specific acceptance steps below. For inference scenarios, cap the test schedule at 50 model requests per scenario, 256 output tokens/request, with the generated retries and concurrency limits; start smaller and stop on unexpected behavior. These limits bound activity, not a guaranteed bill. Track cumulative actual/estimated spending against the original total; billing may lag.
6. Capture sanitized outputs and denied-access results without logging tokens or document bodies. Record the observed result of every acceptance criterion, including failures and not-run checks.
7. Run a refresh plan and inspect drift. Clean up in the same session, then verify state and owned resources are gone. Never leave an uncertain cleanup silently marked passed.

For storage, `scripts/aws-storage-live.py --help` describes the existing bounded apply/test/cleanup runner. There is not yet a qualified automatic live runner covering all six compute scenarios. Do not mistake the local `aws-scenario-live.mjs` prompt runner for AWS deployment automation.

## 5. Scenario acceptance matrix

Use [fixtures.json](fixtures.json) for synthetic inputs. The checkboxes in each scenario README remain pending until actual deployed evidence is recorded.

### 02 — document statistics

Invoke the published live alias as the scoped operator with `{"text":"Hello Sydney\nAWS"}`; expect 3 words and 16 characters. Verify Unicode with `{"text":"Hi 👋"}`: 2 words, 4 code points. Submit a non-string `text`, invalid JSON and a string exceeding the generated input-byte limit; each must be rejected. Invoke from an identity without the permission and record denial. Change the implementation through the product, publish a new version and observe alias/version behavior; exercise rollback to the previously qualified version. Do not treat an administrator's successful invocation as a least-privilege test.

### 03 — asynchronous documents

Upload the text fixture to the private source bucket and retain its version ID. Poll the results table with a bounded deadline for the bucket/key/version record and expected count. Send the same valid event twice and confirm a single correct result. Publish a new object version and confirm a separate version-specific result. Send a malformed/poison message to the source queue, observe retries and eventual DLQ delivery using the configured visibility/retry timings. Correct the source condition and replay a valid event; verify recovery without corrupting prior results. Record queue depths and any alarm behavior; an alarm without a working notification destination does not prove operator notification.

### 04 — model summary

Invoke the alias with the synthetic summary fixture and the reviewed regional model. Verify the answer is grounded in the supplied facts, not merely nonempty. Capture bounded token usage and latency. Reject oversized input before inference. Test access denial with an unauthorized caller and model denial through an isolated reviewed test identity/configuration. Local tests cover throttling responses; leave live throttling marked not run unless a controlled test actually exercises it—do not flood Bedrock. Inspect logs for accidental document/input disclosure. Real answer quality needs human review.

### 05 — cited answers

Seed the bounded catalog using generated `manage-catalog.py` and `CATALOG.md`; use explicit ACLs and the authorized identity mapping. Ask the retention question and verify the cited document ID/version and supported answer. Ask the unsupported lunar-office question; expect insufficient evidence and no fabricated citation. Update retention from 30 to 45 days and verify the new version is used; delete the document and verify it is no longer evidence. Run from the actual authenticated channel. A local mock model or a directly invoked Lambda does not prove the deployed API or browser channel.

### 06 — permission-aware answers

Provision distinct isolated Alice and Bob principals with only generated caller-role/API permissions. Map each to its synthetic subject and employee region. Seed public/Alice-only/Bob-only and wrong-region documents from the fixture. Ask both users questions that target the other user's distinctive restricted marker. Verify no restricted title, text or citation appears; inspect retrieval-boundary evidence without recording sensitive content. Revoke access, repeat within the agreed authorization bound, and test unknown/disabled identities and missing region mappings. Exercise revocation during generation to verify the final authorization recheck. The current bounded runtime rechecks identity/documents before model invocation and response delivery; external source permissions use a short lease (up to 300 seconds), which must be measured in live tests.

### 07 — source contracts and web channel

Run the shipped connector contract tests first; they use loopback normalized-contract servers, not Microsoft/Atlassian tenants. Follow generated connector documentation to sync a synthetic complete snapshot into the deployed catalog. Verify create/update/delete and ACL propagation. Interrupt a sync, restart it and verify journal recovery; stop the source server and check retry behavior and permission-lease expiration. Expired source permissions must fail closed.

Provision a test browser user with generated `manage-web-users.py` and `WEB.md`. Complete the real Cognito password/MFA flow, OAuth state/PKCE exchange and web query through CloudFront. Verify citation display, unknown-user denial, disabled-user behavior, expired-token denial and that another user's evidence is inaccessible. Confirm the assets bucket cannot be read anonymously. Local browser tests with fake OAuth transport do not qualify real Cognito. Teams remains future scope. Native SharePoint/Confluence API compatibility and real-tenant authorization remain explicitly unverified even if this contract test passes.

## 6. Cleanup and evidence publication

Retain an inventory before applying and a write journal before seeding data. Delete only synthetic records/object versions owned by the run. Empty versioned buckets by exact owned version IDs; do not enable broad `force_destroy` or delete unrelated content. Review a destroy plan limited to the run's Terraform state, apply it, verify empty state, then remove separately created owned IAM operators/test users. Check for residual log groups, queues, versions, tables, CloudFront distributions and Cognito resources; allow service deletion propagation before declaring success. Keep the CloudFront distribution disabled/deleting status distinct from fully deleted.

Privately retain configuration, saved create/destroy plans, state history, receipts and test logs. Publish only reviewed sanitized evidence: input/config hashes, timestamps, test names, results, limitations, cleanup verification and costs with confidence/measurement timestamps. Never publish credentials, real principal ARNs, account-bound variables or Terraform state. Append new evidence with a new run ID; preserve failed history. Update `results.json` and the archive manifest only from runner observations.

The archive creation script is `scripts/archive-aws-examples.mjs`; its source run IDs are pinned so rebuilding does not silently select newer evidence. `sourceSha256` identifies pre-sanitization bytes; `sha256` identifies the published file. These are integrity records, not third-party attestations.

Maintainers can attach a completed independent local reproduction and browser import run using `node scripts/archive-aws-examples.mjs --local-recheck .local/example-validation/<run> --browser-recheck .local/example-browser/<run>`. Both reports must include seven passing scenarios. A failed report stays in the original evidence directory and must be investigated; this command never turns it into a pass.
