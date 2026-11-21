# X account pilot deployment

Run `python3 hosted/deploy/provision.py --project YOUR_PROJECT --admin-x-id VERIFIED_NUMERIC_ID` to review the concrete resource plan. `--apply` provisions that plan; never infer the administrator from a handle or developer console ID.

Scope: an account/project API only, 0 minimum and 1 maximum Cloud Run instance, 1 vCPU/1 GiB, concurrency 1, 60-second request limit. This permits invited X users to register a profile, receive the one-time USD20 ledger grant, save/download private projects and manage OpenRouter settings. It does not deploy a generation VM, enable model spending or payments, or publish Hosting.

Dedicated `architect` Firestore database, project and build buckets, image repository, runtime/build service identities, encryption secret and scoped IAM are separate from the existing site and ChatGPT resources. Database access is conditioned on the exact named database; the runtime cannot use that grant on the default/ChatGPT databases. Identity verification only receives Firebase user-read permission. The public HTTP endpoint still requires a valid Firebase X token and current whitelist for all application data. `/health` is intentionally public.

Chosen initial region: us-central1, matching existing project compute, without claiming a user-imposed residency requirement. API instance count bounds scaling, not total expenditure. Cloud Run requests, Firestore operations/storage, object storage, image builds/registry and secrets are usage-billed. No managed model calls are permitted until a separate usage/budget broker is qualified. The USD20 balance is a ledger grant, not a real model request or payment.

The build context is an allowlist of hosted Python modules, dependency lock and deployment files. Python base image is pinned by registry digest; pip uses dependency hashes. Generated secrets pass directly to Secret Manager over stdin. No customer projects, local credentials or development environment are uploaded.

Before opening access, deploy deny-all browser rules to only the new named database/storage bucket, configure staging/retired-object lifecycle, verify real X identity/token revocation and account/project endpoints, and prepare a private website PR for CSP and same-origin Hosting rewrites. Website AGENTS requires owner merge and validated-main artifact publication; this script deliberately cannot deploy Hosting.

Rollback: send traffic back to a previously verified account revision, or remove the website rewrite/disable signup through owner-reviewed main. Do not delete customer data or disable the shared Firebase X provider as a rollback.
