# IBM public-only FAQ composition

The anonymous browser/API uses a dedicated Code Engine trusted profile linked only
to this existing project and this new app. The runtime receives Object Reader on
the exact private COS bucket; a separate existing company access group receives
Object Reader and Object Writer on that bucket. Object Writer includes object
metadata and retention operations, not merely PUT; it does not administer buckets
or make them public. Article deletion conditionally replaces catalog.json; no
object DELETE grant or application HTTP editing route is needed. No public-access
group policy is emitted. Reconcile inherited account/group policies, which can
override narrower grants. Public endpoint routing does not mean anonymous storage.

COS uses a global service instance with a single regional data bucket, encryption
at rest managed by IBM and TLS. Control-plane geography requires separate review.
Versioning and seven-day noncurrent expiry aid recovery, not immediate erasure.
The runtime reads only the current catalog, checks it again before returning an
answer and withholds stale/unsupported evidence. Questions/answers are not persisted
or written to application logs. Private networking/customer-managed keys are not
implemented. This public-only application is not a private knowledge assistant.

Existing Code Engine project, namespace/pull-secret, watsonx project and associated
runtime instance remain intact. The profile gets Writer on that exact pm-20
instance; this is broader than prediction-only. Add the generated profile as a
minimum supported project collaborator and verify the association/model separately.
App creation precedes its compute link to avoid a Terraform cycle; health is
liveness, not model readiness. No app API key or end-user identity is invented.

See applications/*/BUILD.md for editor/build/testing commands. Supply a scoped,
expiring destination-owner policy review and test real IAM, compute token exchange,
conditional storage edits, source updates/deletions, model citations/abstention and
latency. The policy review is operator evidence, not a fabricated provider API.
Review current model availability, quotas, processing terms, prices, anonymous
abuse controls and budget policy. Instance/concurrency/token limits are not an
invoice cap. Protect state/variables. Native schema/mocks and local runtime tests
do not establish account-plan or deployed behavior. Obtain authorization before
image publication, cloud access, real plans or deployment; production operating
and state/backup review remain gated.

References:
- https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-iam-bucket-permissions
- https://cloud.ibm.com/docs/iam?topic=iam-iam-service-roles-actions
- https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-upload
- https://cloud.ibm.com/docs/codeengine?topic=codeengine-trusted-profiles-authentication-file
