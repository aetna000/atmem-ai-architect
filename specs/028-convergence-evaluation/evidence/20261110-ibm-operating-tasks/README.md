# IBM operating task checkpoint — partial native wrapper

Implemented fixed initialize/maintain/monitor Code Engine task definitions in the
generator. Separate operator-only SQL credential, no CRT/API service account or
model/object/accounting authority. Only bootstrap receives API/worker SQL password
keys. No secret payload or Terraform-created secret is emitted. Runtime image
ownership/digest gates apply even before application release.

Actual pinned IBM 2.9 schema plus nine native mock plans pass. All 310 JavaScript
tests pass. Eleven independent local fake-CLI cases execute the actual emitted
helper, including isolated private CLI context, exact destination selection and
wait, preview with no cloud CLI, concurrent-operation refusal, permission checks,
failed project selection, malformed account, mixed jobs and duplicate JSON fields.

This is NOT IBM operating-wrapper completion. Cron subscriptions and Cloud Logs
alerts are still pending; no unsupported Terraform cron resource was invented.
No real IBM CLI authentication, native job/SQL execution, scheduler, alert delivery,
cloud plan, publication or deployment ran. Shared historical runtime evidence is
not promoted to new native IBM job execution evidence. Zero complete medium invoice
conversation/export cases are counted. Whole capability/state/Spec Kit integration,
remaining families, final28 rerun and held-out variants remain unfinished.

Vendor CLI/cron source revisions and SHA256 provenance are preserved. Qualification
uses synthetic metadata and fake command processes, without cloud credentials.
