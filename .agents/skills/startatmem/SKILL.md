---
name: startatmem
description: Resume the saved Google Cloud VM for hosted AtMem AI Architect when asked to bring the online platform back. Reuse its preserved deployment; not for creating projects or upgrading releases.
---

# Resume hosted AtMem

An explicit invocation or request to start the hosted platform authorizes restarting the existing VM and resuming its normal compute costs. Do not request the same authorization again. Creating this skill or asking about startup does not itself request a start.

Resolve this skill's real directory, then find its repository root. Read [the pause/resume runbook](../../../hosted/deploy/PAUSE_RESUME.md) and use [the shared helper](../../../hosted/deploy/pause-resume-worker.py). The runbook and saved manifests hold the deployment configuration; the user does not need to repeat it.

Run from the repository root:

```sh
python3 hosted/deploy/pause-resume-worker.py status
python3 hosted/deploy/pause-resume-worker.py start
```

Use `--state-dir PATH` only when the recorded private pause package is stored elsewhere. Do not invent new deployment parameters.

Target project `atmemai`, zone `us-central1-a`, VM `architect-native-worker`, with its retained boot disk and `architect-native-worker-state` disk.

1. Inspect the VM and saved configuration. Confirm the original disks, pinned worker image, startup script, network and service identity are intact.
2. Run the helper's start action for the existing VM. An already running instance should be verified rather than recreated.
3. Verify systemd/container readiness, the worker broker socket and workload service identity through IAP. Do not submit a paid AI request merely to test startup. Heartbeats are job-scoped; do not invent an idle heartbeat.
4. Check any endpoint refresh required by the runbook. An ephemeral public IP may change; report the actual result and remaining readiness failures.

Do not deploy a newer image, re-provision infrastructure, format or replace disks, reset data, rotate secrets or enable new services as part of a routine start. If preserved resources are missing or configuration has materially changed, report the exact mismatch and use the recorded recovery plan before taking a different action. Never claim service readiness solely because the VM says `RUNNING`.
