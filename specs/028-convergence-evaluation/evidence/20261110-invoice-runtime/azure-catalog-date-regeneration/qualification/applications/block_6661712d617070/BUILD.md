# Generated public FAQ application

Use an isolated Python 3.13 environment. Install test-requirements.lock with
--only-binary=:all: --require-hashes, then run faq_acceptance.py -v. The source
tests use synthetic public articles and explicit transport fixtures. They do not
establish real IAM, model quality, service availability or deployment behavior.

Build this directory as Linux/amd64 with its emitted Dockerfile, run startup and
acceptance checks on the exact image, scan it and retain source/image digests.
Obtain authorization before authenticating to a registry or publishing an image.
Supply the reviewed immutable release inputs required by this provider's Terraform.
The runtime runs nonroot; use a read-only filesystem and writable temporary space
where the destination supports it. Local read-only checks do not prove the cloud
host applies identical filesystem isolation.

The anonymous API can only read the dedicated public catalog and invoke the
reviewed regional model. It has no HTTP editing endpoint. Never grant the runtime
catalog write, private-source, account-admin or model-policy-write permissions.
Review inherited destination IAM in addition to the emitted grants. An explicit
public marker does not automatically classify or approve document content: the
authorized editor is responsible for selecting genuinely public help articles.

Authorize the separate editor using the emitted native role and a short-lived
credential. Keep credentials and article files outside this source bundle. Use
public_catalog_admin.py --help, then inspect, init, upsert or delete as appropriate.
Initial creation requires --expected-version create. Later edits require the exact
observed version and --confirm-write. The native conditional write must succeed;
conflicts require reloading and reviewing the change. Never retry a write blindly
after an unconfirmed response. Editor flags express intent; the cloud IAM role
remains the authorization boundary. Do not pass a browser user token as an editor
credential. Token files must be operator-owned and private.

Seed the catalog explicitly before allowing traffic. Initialization reads every
file in a dedicated public .txt/.md directory, supports spaces/Unicode names and
creates stable distinct source IDs. It rejects symlinks, invalid UTF-8, oversized
files or unsupported entries rather than silently omitting articles. Later updates
and deletions change the current manifest; any retained backup versions require a
separately reviewed operator recovery path. The API never falls back to cached or
inaccessible source data. A changed source during inference withholds that answer.

The bounded lexical retriever admits up to 100 articles of 30000 UTF-8 bytes each;
the acceptance project starts with twenty. It supplies at most two full relevant
articles, without cutting sentences. Citation IDs and quotes are independently
verified against that exact evidence. URLs/titles come from the approved catalog,
not the model. Syntax and quote membership do not prove factual entailment: run a
representative real-model answer/citation/abstention evaluation before deployment.

The provider schema remains stable across queries to avoid a new grammar for every
source combination. The bounded synchronous AWS adapter uses independently decoded
JSON, not a claimed provider-constrained grammar: Bedrock's new-schema compilation
can take around 90 seconds and cannot silently fit a 29-second HTTP path. Other
adapters use their documented output modes with the same independent decoder.
Unsupported model/output responses fail closed; no model or region is silently
substituted. The browser does not retry model calls automatically.

Verify current regional model support, data handling, identity/control-plane
processing, quotas and prices with retained evidence. Limits on input, output,
concurrency and instance count are not an invoice cap, availability or latency SLA.
No question/answer persistence or content-bearing application logs are implemented;
review provider/platform logging and retention separately. Private enterprise
connectors, user tenancy, payments and durable workflows are different capabilities.
