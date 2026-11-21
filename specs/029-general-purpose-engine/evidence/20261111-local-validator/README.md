# Controlled local runtime validation — 2026-11-11

Reusable capability: execute a trusted check against exact immutable project bytes
in an isolated local runtime, with working private HTTP and no model/host networking
grant. This is controller foundation; it is not yet exposed through the product UI,
a full system validator, a software release or acceptance of an original project.

## Interfaces and limits

`server/local_validation.py` defines `ValidationSpec` (operator-selected immutable
cached image ID, platform, executable/arguments and bounded time) and
`DockerValidationWorker.run(archive, expected_digest, spec)`. No raw-command HTTP/MCP
endpoint exists. Future project-facing scheduling must authorize artifact ownership
before invoking the worker and retain receipts against the exact artifact digest.

Only an explicit existing local Unix daemon is permitted. The Docker client uses a
fresh empty config and limited environment; it does not read registry credentials,
pull/build/publish images, change the current Docker context or mount host directories.
Input travels over stdin and is checked for digest, size, entry count, path traversal,
duplicates and linked/special entries. Trusted bootstrap code extracts root-owned
read-only source, drops supplementary groups/UID/GID, then runs the check as 65532.
`no-new-privileges`, empty effective/permitted capabilities, read-only root, private
bounded tmpfs, network-none, CPU/memory/process/time/output limits apply. The only
bootstrap capabilities are SETUID/SETGID, cleared before untrusted code executes.
The model worker never receives the Docker socket.

The actual runtime is Linux/amd64, cached Python image
`sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20`,
**Python 3.13.18**, in the existing local `architect-qualification` Colima VM. Other
running containers were left in place. This does not establish Python 3.12 managed
runtime/SDK compatibility, target-cloud behavior or hosted tenant isolation. No real
cloud accounts, deployment, image registry or provider credentials were used.

Check exit success is separate from complete evidence. Reported skipped checks are
incomplete; zero unittest tests or missing test-count output cannot pass. A command
receipt is not an independent requirement oracle. Unsupported tools, dependencies,
required writes to source or additional services need explicit runtime contracts;
the worker does not silently install packages or fall back to a host shell.

## Observed evidence

- `receipt.json`: six real-container control probes. Positive: nonroot, empty groups,
  zero effective/permitted capabilities, no new privileges, source-write denial,
  absent host mounts/Docker socket/host environment canary, denied raw sockets and
  host/external connections, plus actual private loopback HTTP request/response.
  Negative: timeout, output overflow, deliberately skipped evidence, zero tests and
  archive traversal all remain failed/incomplete as required. No host canary
  connections occurred. Test containers were removed.
- `before-zero-exit-expectation.*`: retained failed qualification expectation. This
  pinned Python returns exit **5** for zero tests. The controller correctly failed
  the check; the probe originally expected “incomplete.” Correcting that expectation
  did not change acceptance gates. The final six-probe receipt passes.
- `native-python/receipt.json`: 18 generated Python tests pass on unchanged emitted
  source. `native-http/receipt.json`: the generated real HTTP smoke passes inside the
  private container loopback. It had been blocked under the model worker's host policy.
- `specialized-python/receipt.json`: 17 generated tests pass, **zero skips**. The
  previously skipped HTTP class now runs, including five simultaneous HTTP requests,
  input rejection and synthetic provider failure/recovery. Source was not patched.
- `measurement-python/receipt.json`: nine generated tests pass on the separately
  captured non-cloud measurement-library ZIP. This demonstrates transfer beyond the
  support-ticket domain.
- `native-independent-http.json` and `specialized-independent-http.json`: **18
  independently authored checks each** exercise real HTTP success, validated response
  shape, malformed/duplicate/empty/oversized/multibyte/boolean input, denied callers,
  content type, static assets, five concurrent requests, synthetic model timeout,
  recovery and absence of the ticket canary in stdout/stderr. The oracle hash and
  original source hashes are recorded in each receipt.

The independent HTTP adapters are explicitly evaluation-only knowledge of the emitted
harness interfaces (`LocalHandler`/`Request`, route, synthetic token and transport
injection). They are not production scenario dispatch or repaired exports. They
exercise generated application code through its real HTTP adapter, but identity and
model transports remain synthetic. No actual OAuth/JWT login, Cognito/API Gateway/
Bedrock emulation, real model quality, provider integration, regional residency,
browser user journey or full ticket-system acceptance is established. The original
accepted count therefore remains **0/28**, with no specialized quality advantage.

## Reproduction

`scripts/engine-evaluation/check-local-validator.py` runs the six actual control probes
against the existing named local VM and cached image. It uses synthetic canaries only.
`server.tests.test_local_validation` has three fast contract-negative tests; these
complement, and do not substitute for, the real container probes.

`scripts/engine-evaluation/replay-container.py` takes an immutable artifact ZIP/digest
or an exact source directory plus original generation manifest, an explicit local
endpoint/image and a trusted command after `--`. It never repairs source. Output paths
must be new, preserving earlier evidence. `scripts/engine-evaluation/check-paired-http.py`
replays the separate original-brief HTTP diagnostics without modifying their artifacts.

Next: bind operator-reviewed validators to project-scoped artifact/evidence jobs and
product progress; add actual identity/service connection and complete browser journeys,
including denied/failure/recovery paths. Preserve unsupported scope and all original
requirements. Cloud deployment is not needed for the authorized local programme.
