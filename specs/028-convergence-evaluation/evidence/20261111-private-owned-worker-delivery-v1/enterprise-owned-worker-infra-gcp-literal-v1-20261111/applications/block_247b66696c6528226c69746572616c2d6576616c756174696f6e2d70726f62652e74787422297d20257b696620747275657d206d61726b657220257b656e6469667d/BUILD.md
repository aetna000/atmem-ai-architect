# Private application delivery

Build this exact directory as Linux/amd64 with the emitted Dockerfile and hash lock.
The API is the default command. The manifest also records the dedicated worker and
operator commands. Keep parser/OCR tools in their separate reviewed artifact: no
document parser, Java runtime or Docker daemon runs in this credentialed worker.

Build the supplied parser recipes separately, in this order, and record their
actual inspected source/image identities before using them in native configuration:

docker build --platform linux/amd64 -t atmem-private-pdf-base:local parser/pdf
docker build --platform linux/amd64 --build-arg PDF_PARSER_IMAGE=atmem-private-pdf-base:local -t atmem-private-document:local parser
docker build --platform linux/amd64 -t atmem-private-application:local .

Local tags are build handles, not immutable publication evidence. Keep the exact
image IDs/build receipts and obtain authorization before any registry publication.

Supply the approved deployment as ENTERPRISE_DEPLOYMENT_JSON or an absolute
ENTERPRISE_DEPLOYMENT_FILE mount. Supply exactly one form, never conflicting sources.
The API reads only its deployment metadata; it does not construct a parser or model.
For an implemented native worker, supply ENTERPRISE_DOCUMENT_EXECUTOR_JSON or its
absolute FILE mount from the same Terraform output and parser build receipt. The
worker checks provider, parser revision, native destination and worker identity before
reading source/encryption secrets or SQL. No arbitrary plug-in, executable or URL
can be selected through this configuration. Default worker concurrency is two;
ENTERPRISE_WORKER_CONCURRENCY accepts one to four after capacity/quotas are reviewed.

AWS and Google native document loading are implemented locally. Azure/IBM loading
remains an implementation requirement; their application source/dependency emission
does not advertise a complete worker or substitute another cloud. No complete
private capability is promoted by these files.

The configured worker attaches the durable cleanup ledger and runs recovery alongside
question processing. Runtime startup never initializes schemas, adopts existing SQL
state, creates company membership or generates replacement encryption keys. Use the
operator lifecycle with separate existing native SQL identities before enabling it.
Keep corporate OIDC/source registrations and approved directory mappings intact.

Preserve image/source digests, reviewed dependency/security evidence and actual
destination artifact publication records. Parser revision, local image configuration
digest and registry manifest digest are distinct identities; never invent or equate
them. Full application/worker/database/model/source networking, secrets, enrollment,
artifact publication, operations and Spec Kit composition remain mandatory before
whole-project acceptance. No account plan, publication or deployment ran here.
