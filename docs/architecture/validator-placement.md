# Explicit validator placement and recovery

Local operator configuration can register several executors behind the existing
backend check service. This separates a validator's immutable image/platform/
command/policy from the operator's execution placement. No workload, cloud,
project name or model answer dispatches to a hardcoded machine. The browser/native
caller still supplies only a registered validator ID and owned package/check ID.

`ATMEM_ARCHITECT_ENGINEERING_VALIDATOR_WORKERS` is a JSON object, for example:

```json
{
  "browser-runtime": {
    "endpoint": "unix:///absolute/operator/browser/docker.sock",
    "isolationProfiles": {
      "chromium-userns-v1": {
        "path": "/absolute/operator/reviewed-browser-policy.json",
        "sha256": "<actual reviewed policy digest>"
      }
    }
  },
  "native-runtime": {
    "endpoint": "unix:///absolute/operator/native/docker.sock"
  }
}
```

The digest placeholder must be replaced by the actual reviewed value accepted by
DockerValidationWorker; arbitrary profiles are rejected. Config supports at most16
named workers. Each entry accepts only endpoint and optional isolationProfiles.
Transport remains an explicitly approved local Unix socket; no TCP endpoint,
privileged option, image pull, context switch, host mount or discovery is added.
Definitions copy their policy references so later input-dictionary edits cannot
change them. Sockets/policies are checked at instantiation. Missing ones remain
unavailable and can be retried when explicitly restored; no peer is substituted.

An `ENGINEERING_VALIDATORS` entry can select `"workerId":"native-runtime"`.
Worker IDs are operator-owned names, not a new request parameter. The existing
ENGINEERING_VALIDATOR_ENDPOINT and ENGINEERING_ISOLATION_PROFILES still supply the
legacy default for entries with no workerId. Named-only configuration needs no
default. Adding unrelated named workers does not change valid legacy contract
hashes or public payload shapes. Changing an explicit assignment changes its
contract even if the command/artifact is unchanged; historical receipts remain.

Catalog/plan placement status identifies configured, worker_unavailable,
isolation_profile_unavailable or runtime_observation_mismatch. Configured/available
means that the executor/profile registration is available, not a live daemon,
image, SDK, kernel capability or application readiness guarantee. Actual execution
still verifies the cached exact image and requested platform and never pulls or
changes platform. Registered missing/unqualified placements cannot enqueue work.

Named placements require any pinned runtime observation to match the selected
worker identity and full worker policy. Version2 context/process-control receipts
require that match even under legacy default configuration. Mismatched facts are
omitted from the public runtime catalog, its runnable contract is absent, and the
check is unavailable until the operator observes/registers the correct context.
Legacy version1 image-only observations retain their existing shape/contracts;
they remain image-metadata snapshots rather than kernel evidence. See
[runtime observations](runtime-observations.md) for provenance and freshness limits.
No snapshot or endpoint digest proves the current boot or grants permissions.

Check admission binds the worker identity, policy and explicit logical assignment
into the durable contract. Execution retains that admitted executor object while
queued; changing the registry/default cannot retarget it. A changed admitted
identity/policy fails before execution. Queue/cancellation limits remain shared
across executors. Native working-file checks and finalization use the same path;
there is no raw execution/worker-setting route exposed to model or browser input.

After receiver loss, cleanup resolves the durable check's saved worker identity
among currently approved executors. It does not use the current validator mapping
or current default as a substitute. A renamed approved entry with the exact
original identity can clean up; a different endpoint cannot. Missing original
workers leave recovery_required until explicitly restored. Cleanup uses the saved
check UUID, confirms container absence through successful daemon queries, never
reruns work, and preserves prior package bytes and receipts. This also supports
legacy saved jobs whose original default is now registered under a recovery name.
Changing a worker policy may invalidate new checks/observations; cleanup can still
remove the old container on that same original endpoint without executing code.

Worker identity currently hashes the endpoint; it is not machine/boot attestation.
Operator reassignment of the same socket to another daemon therefore still needs
fresh context qualification. This change supplies neither automatic freshness
leases nor hosted multi-tenant worker/store security. Hosted adapters must preserve
the same scoped immutable contract and qualify their own transport/authorization/
transactional leases. Browser access remains through the backend session service.
