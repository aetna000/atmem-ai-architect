---
name: shutdownatmem
description: Pause the saved Google Cloud VM for hosted AtMem AI Architect when asked to stop or shut it down, preserving its deployment and data for fast restart. This is not a resource teardown.
---

# Pause hosted AtMem

An explicit invocation or request to stop the hosted platform authorizes the routine stop below; do not ask for the same authorization again. A request for instructions or status alone does not authorize a state change.

Resolve this skill's real directory, then find its repository root. Read [the pause/resume runbook](../../../hosted/deploy/PAUSE_RESUME.md) and use [the shared helper](../../../hosted/deploy/pause-resume-worker.py), rather than reconstructing deployment settings from chat.

Run from the repository root:

```sh
python3 hosted/deploy/pause-resume-worker.py status
python3 hosted/deploy/pause-resume-worker.py stop
```

Use `--state-dir PATH` only when the recorded private pause package is stored elsewhere. Do not invent new deployment parameters.

The saved deployment is project `atmemai`, zone `us-central1-a`, VM `architect-native-worker`. Use explicit project/zone arguments, never the current gcloud project as authority.

1. Inspect and capture the current VM configuration using the helper. Keep private startup metadata and recovery files under its ignored local state directory.
2. Run the helper's stop action. Reuse the existing VM; an already stopped VM is a successful no-op.
3. Verify `TERMINATED`, no attached ephemeral public IP, and both original disks still attached. Retain snapshots, image digests, service identity, network and deployment configuration.
4. Report the actual stop result and saved restart instructions. Compute has stopped; retained disks, backups and registry storage can still incur charges.

Never delete the VM, disks, snapshots, images, buckets or Firebase/Firestore data as part of this skill. Do not alter machine size, startup configuration, billing or the deployed release. The user's intended workflow is **pause now, start the same deployment later**.
