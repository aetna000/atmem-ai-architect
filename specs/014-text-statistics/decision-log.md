# Decisions

- `data.implementation=text-statistics` selects the tested application. A Lambda label never generates arbitrary application code.
- Supporting execution IAM, log group, published version and alias belong to the component. Existing callers use typed `lambda-invoke` edges and required same-account ARN inputs.
- Word counts split Unicode whitespace; character counts use Unicode code points. Accept exactly one text property, reject malformed/oversized input, and never log document text.
- Proposed defaults are explicit Terraform inputs, not source requirements: 128 MiB, 10 seconds, concurrency 1, 64 KiB input and 30 days logs.
- Publish immutable Lambda versions; the live alias can select a prior published numeric version for rollback.
- Production exports declare a separately configured S3 state backend with native lock files. Local state remains a staging-validation choice.
- Project format 2.3.0 adds typed bindings, access and implementation fields; existing 2.x files remain readable with absent fields unimplemented.
- Replace archive-provider packaging with a deterministic Python build: fixed ZIP metadata, sorted files, no bytecode, explicit artifact hashes. SDK workloads include hash-locked wheels; tests import the packaged handler.
- Read-only account evidence found a regional Lambda concurrency quota too low for reserved limits. Export account preflight checks rather than silently removing the limit.
