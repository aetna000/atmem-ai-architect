# Pause and resume the hosted Architect worker

The retained production worker was paused on 2026-11-17. Google Cloud reports `TERMINATED`, both disks remain attached, and the ephemeral public IP has been released. No VM, disk, snapshot, image, project data, IAM binding, secret or website resource was deleted. The Firebase website and account API remain deployed; native project work waits for this worker.

## Saved deployment

The non-secret binding is [worker-pause-config.json](worker-pause-config.json). The pause helper targets this exact existing VM ID, so a different VM reusing its name is refused.

| Setting | Retained value |
|---|---|
| Google project | `atmemai` |
| VM / zone | `architect-native-worker` / `us-central1-a` |
| VM ID / machine | `2465606325247425787` / `e2-medium` |
| Boot disk | `architect-native-worker`, 30 GB standard, device `persistent-disk-0`, boot auto-delete true |
| State disk | `architect-native-worker-state`, 30 GB standard, device `architect-state`, auto-delete false |
| VPC / subnet | `architect-workers` / `architect-workers`, `us-central1` |
| Internal IP | `10.91.0.2` |
| Workload identity | `architect-worker@atmemai.iam.gserviceaccount.com` |
| State mount / container path | `/mnt/disks/architect-state` / `/var/lib/architect/runtime` |
| Worker service / container | `architect-native-worker.service` / `architect-native-worker` |
| Snapshot policy | `architect-state-daily`, seven-day retention, still attached |
| Account API | Cloud Run `architect-accounts`, `us-central1` |
| Saved projects | Firestore database `architect`; bucket `atmemai-architect-projects` |
| Container storage | Artifact Registry repository `us-central1-docker.pkg.dev/atmemai/architect` |
| Site | `https://atmem.ai/architect` |

The exact deployed worker image and startup-script SHA-256 are pinned in the binding. The VM retains the actual startup metadata, disk attachments, service account, network and deletion protection. Restart reuses that preserved deployment. A newer application deployment remains a separate operation.

## Commands

Run from the repository that contains the helper, with an authenticated operator `gcloud` account authorized for this project:

```sh
python3 hosted/deploy/pause-resume-worker.py status
python3 hosted/deploy/pause-resume-worker.py stop
python3 hosted/deploy/pause-resume-worker.py start --dry-run
python3 hosted/deploy/pause-resume-worker.py start
```

`status` is the default and performs read-only inspection. `stop` preserves every disk, image and backup, records the deployment, and checks stopped state plus ephemeral IP release. Repeating it on a stopped VM preserves the existing pause baseline; configuration drift is reported instead of silently adopted.

`start` invokes `gcloud compute instances start` on the retained VM. It compares the current configuration with the saved pause baseline before and after starting. When no private baseline is available, it checks the tracked machine type, exact disks/devices/sizes/auto-delete settings, service account, network/subnet/internal IP and startup hash. The helper never provisions a replacement or restores metadata from an old file.

Starting resumes existing queued user work and its configured model budgets. The readiness probe submits no jobs or model requests. It verifies, through IAP, the systemd service, running container, state mount, accepting private broker socket and held worker singleton lock. The VM configuration verifies the workload service-account identity. This runtime has job-scoped heartbeats; it has no idle global heartbeat, and the helper does not claim one. A failed readiness check reports that the VM may be running and needs inspection.

The readiness limit defaults to 300 seconds; use `--ready-timeout 30..600` to change it. `status --check-ready` probes an already running worker. Review the returned status before claiming the online platform is ready.

The ephemeral IP may change on restart. This deployment receives work from the Firestore queue and is reached administratively through IAP; the recorded website/Cloud Run integration does not depend on the VM's public IP. No application DNS change is normally required. Refresh any separately maintained IP allowlist if one was added later.

## Private pause package

The default private directory is `.local/worker-pause-resume`. Override it with `--state-dir /absolute/private/path` on every command when using another operator checkout. Keep this directory outside source control and retain it when moving the helper into the stable operations checkout.

- `latest-pause.json`: sanitized configuration and hashes, excluding secret metadata values.
- `startup-script-preserved.sh`: optional **sensitive, untracked** raw startup backup. Pattern scanning is limited and does not prove it secret-free. The helper does not use it to overwrite the VM.
- `last-operation.json`: the observed stop/start result.

The one-time shutdown audit and before/after inventories are in `.local/cloud-shutdown-2026-11-17`. Existing `.local/worker-deployment` was preserved unchanged. Actual credentials remain in the existing Google account, Secret Manager and workload identity; they are not stored in this runbook or tracked binding.

## Retained costs

Stopping removes VM CPU/memory usage charges, and the ephemeral IP is released. Retaining disks and recovery assets is necessary for this pause/resume setup and continues storage billing. [Google's stopped-instance behavior](https://docs.cloud.google.com/compute/docs/instances/suspend-stop-reset-instances-overview), [disk pricing](https://cloud.google.com/compute/disks-image-pricing).

At the published `us-central1` standard-disk rate of USD0.04 per provisioned GB-month, the two 30 GB disks are **about USD2.40/month before credits, discounts and tax**. The two retained snapshots currently report only 7,390,720 stored bytes; snapshot storage at that size is below one US cent per month. The unchanged daily/seven-day policy continues normal incremental backups. Rates and future usage should be checked in Cloud Billing. [Block-storage rates](https://cloud.google.com/products/block-storage).

The whole retained `architect` Artifact Registry repository currently reports about 2.84 GB, including account-API images. Its gross storage is approximately USD0.27/month before the shared free allowance; worker-only cost is no greater than that total. Build-source bucket storage, saved projects, Firestore, Secret Manager and request-billed Cloud Run services remain separately billed by usage. No zero-cost promise is made for the whole Google account. [Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing).

No VM reservations, commitments or managed instance group were found in this project's shutdown inventory. No snapshot schedule or retention setting was disabled. Prior incurred usage remains on the bill.

## Deployment source and recovery boundary

The original deployment flow is recorded in [provision-worker.py](provision-worker.py), [build-worker-image.py](build-worker-image.py), [runtime-images.json](runtime-images.json) and [README.md](README.md). The stopped VM's metadata is authoritative for its currently deployed startup script and image.

Routine resume uses the existing-VM helper, **not** `provision-worker.py --apply`, an image rebuild, disk formatting, or a new VM. A local quoting defect in the provisioner's generated registration insertion was repaired and dry-run validated; no provisioning was applied. Preserve the private state disk and existing recovery assets if a later explicit migration is planned.
