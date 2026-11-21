# Explicit check placement and original-worker recovery

GE-006 source checkpoint. Previously every validator used one global Docker
worker. The observed Google AMD64 userspace/ARM-kernel restriction and native ARM
browser requirements showed why an image/platform alone cannot choose execution
context. The engine now accepts explicit operator-owned worker assignments without
case/provider/domain dispatch, target substitution or image pulls.

## Mechanism and compatibility

Operator ENGINEERING_VALIDATOR_WORKERS maps bounded logical names to local Unix
sockets and independently reviewed profile references. A validator's optional
workerId selects exactly that entry. Missing workers/profiles are unavailable;
none falls back to the legacy default or a peer. Named-only service, native check
catalog/working checkpoints, automatic planning and manual checks use one path.
Browser/model input still accepts registered check IDs only; worker/endpoints/
commands remain forbidden request fields.

Contracts bind named placement plus actual worker identity/policy and any pinned
runtime observation. Queued work retains the admitted executor object rather than
reading a later global mapping; changed admitted identity/policy is rejected before
execution. Legacy valid registrations, default behavior and manual contract hashes
remain compatible. An unrelated named entry does not invalidate legacy evidence.

Named observations must match the selected endpoint identity and worker policy.
Context-bound version2 observations also require that match under legacy default
configuration. Mismatched facts are omitted, their runnable catalog contract is
absent, and checks cannot enqueue until the operator supplies correct evidence.
Valid legacy image-only observation shapes remain unchanged. Available/configured
means registered worker/profile, not a daemon-health, image/SDK/control, current
boot or full application guarantee. Endpoint identity is still a hash of its URI;
there is no automatic freshness lease or machine attestation.

Recovery resolves the saved check identity among explicitly approved executors,
including a renamed original or an original legacy default retained under a named
recovery entry. It does not resolve the current validator or default as a substitute.
Unknown originals stay recovery_required. Cleanup confirms absence through successful
queries, never reruns work, and preserves immutable package/history. Reviewed policy
changes can invalidate new observations while cleanup of the original container
remains possible on that same endpoint. No SQLite migration or cloud access is added.

API/configuration/compatibility limits and rollback are documented in
`docs/architecture/validator-placement.md` and runtime-observations.md.

## Actual runtime evidence

receipt-v2.json covers one immutable synthetic package containing independent
browser and process/SQL tests. It is not a browser-connected database application,
a client project, native-model run, original28 acceptance or alpha.5 release.

- ARM64 worker: actual Chromium with chromiumSandbox:true and reviewed profile;
  real page interaction passes1 Node test.
- Separate full AMD64-kernel worker: actual typed no_new_privs/seccomp filter,
  requested process architecture and equality with the fresh observed boot hash,
  plus actual PostgreSQL17.11 pass3 Python tests. No required filter/platform was
  removed or changed. Both validators use actual ValidationJobs with no default.
- A real ARM executor paired with AMD64-context facts is rejected, both with an
  explicit wrong workerId and with a changed legacy default. Missing named workers
  are rejected too. No extra check rows or execution are created by these cases.
- A separate actual receiver starts a durable AMD64 check. The evaluator observes
  its running test marker, kills only that owned receiver with SIGKILL, and reopens
  its durable store with the validator removed and ARM as the new default. A
  controlled ARM peer container has the same check UUID. Recovery removes only the
  original AMD64 container; that peer survives until explicit fixture cleanup.
  The artifact bytes are unchanged, the record becomes supervisor_restart, and
  no additional check/replay record is created. This is a real receiver/process
  loss, not a simulated row update. Native product/model sessions are never killed.

Fresh browser image-only and AMD64 context/process observations are retained as
original receipts, including private worker provenance and complete probe output.
They expose no credentials or raw boot UUID. The old failed Google check history
is untouched. Real test sources, eight evaluator/engine source snapshots, private
config/SQLite and logs remain on MEM0 under
`.local/external-artifacts/validator-placement/v1/real-v2`; receipt source hashes
match final product bytes. No source is mounted from the host into checks. Default
container/time/output/PID/memory/network/capability bounds are unchanged.

cleanup-v1.json independently confirms all experiment containers and owned Docker
CLI processes are absent using exact UUIDs and successful daemon queries. No broad
prune, owner VM restart, private project read/write or preview activation occurred.
A source archive and host scratch from the killed receiver stay in its owned MEM0
evidence directory; they are data, not running resources. The prior real-v1 result
and component phases remain historical evidence, rather than being rewritten.

## Tests and reproduction

67 focused lifecycle/API/native-tool/observation/registration tests pass, including
missing worker, missing profile, wrong receipt worker/policy, queued reassignment,
changed admitted policy, original-worker recovery after validator removal,
legacy-default recovery and operator-only worker ID validation. Full471 server
checks,555 JavaScript checks and production build pass; the existing chunk-size
warning remains. These counts do not establish native-model quality or held-out
application acceptance.

Run focused tests with the normal server environment:

    .venv/bin/python -m unittest server.tests.test_validation_jobs server.tests.test_validation_workers server.tests.test_runtime_evidence server.tests.test_engineering_tools server.tests.test_engineering_local_worker server.tests.test_engineering_routes -v

For a fresh receiving checkout, prepare-real.py accepts --arm-endpoint,
--amd64-endpoint and --browser-policy; workers.example.json/validators.example.json
pin the tested images/commands without private host paths. It validates definitions
and refuses to replace existing inputs. Then run scripts/engine-evaluation/
observe-runtime.py against each actual context using those validators: node with
the browser profile for placed-browser-tests, and python --process-controls
--python-package psycopg --python-package procrastinate for placed-process-tests.
Use browser-observation-v1.json and amd64-observation-v1.json under the bulk root
as output names. Both command/profile/image contexts must already be approved and
cached; setup installs/authenticates/runs no application or cloud resources.

Real evaluator run-real.py --attempt NEWALPHANUMERIC requires the explicitly
owned two cached Docker contexts, operator profiles/registrations and pinned fresh
observations prepared under the bulk directory. It creates a new evidence directory
and owned SQLite/source/receiver/container resources, then cleans only those UUIDs.
crash-receiver.py is its controlled child, not an app or cloud deployment script.
Do not point this fault-injection evaluator at owner/native product processes.

Manual test card: configure named workers and assign validators; inspect the catalog,
run an immutable package through each selected runtime, remove a named placement
and confirm it stays unavailable despite an available default. Recover a genuinely
uncertain owned check only after restoring its original approved worker; verify no
check replay and inspect the retained failed receipt before explicitly retrying.
Rollback configuration/source after stopping its own supervisor; retain original
worker access and check records for cleanup. Do not delete uncertain records,
redirect cleanup or rewrite old evidence to activate an incompatible configuration.

Next start/qualify the native IBM transfer using explicit appropriate runtimes,
then finish application/receiving and frozen alpha.5. All26 remaining originals,
unfamiliar systems and the full ten runnable increments remain in scope. Overall
originals2/28, four increments offered, owner acceptance0, measured quality unknown.
