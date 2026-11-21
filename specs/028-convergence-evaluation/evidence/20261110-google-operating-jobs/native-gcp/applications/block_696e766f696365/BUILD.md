# Invoice application images

This directory contains API/worker source and a separate bounded PDF/OCR image.
Build both as Linux/amd64 and retain source/image digests and security reports.
Use only the emitted exact wheel/native-package hashes and pinned container bases.
The IBM lock deliberately uses dateutil 3.0.0 required by its SDK; the composed queue
must be qualified with this dependency set, rather than borrowing another provider's
test result. Installer tools are removed from the application delivery image.

The API command is the image default. The dedicated worker command is
python -I /app/invoice_worker.py. Parser hosting overrides its default CLI with
python -I /app/invoice_parser_service.py. Do not run a Docker daemon in the worker.
Keep the parser in a separate workload with no database, model, object-store or
outbound action authority. Its private TLS ingress/caller restrictions are required
native infrastructure, not an anonymous public HTTP service. Runtime identities,
network and destination acceptance require separate destination checks.

The API never receives a model credential or outbound action secret. The worker
splits extraction and delivery into bounded child processes without database
configuration in their environments. The 180-second extraction deadline includes
object retrieval, up to 110 seconds of parsing/OCR and model/commit overhead inside
a 600-second domain lease. Delivery is bounded to 45 seconds; unknown external
outcomes require a verified same-key/same-payload idempotency contract or operator
reconciliation. A failed new attempt cannot erase an older uncertain side effect.
Child deadlines are not an OS sandbox; untrusted PDF parsing stays separate.

Default worker concurrency is one, matched to one parser slot. Twenty uploads
are admitted into the durable queue; they do not become twenty simultaneous OCR
processes. Scale worker/parser capacity together only after throughput, model quotas
and backpressure are tested. Capacity settings are not a price cap or SLA.

Keep credentials outside this directory and source control. Mount native CA and
secret files and supply the generated deployment environment. SQL role/bootstrap,
membership, retention/restore and reviewed external accounting contract are required
operational steps. Building this application does not prove those resources exist
or declare the complete project ready. Obtain authorization before publication,
account plans or deployment. Local checks do not establish cloud IAM or availability.
