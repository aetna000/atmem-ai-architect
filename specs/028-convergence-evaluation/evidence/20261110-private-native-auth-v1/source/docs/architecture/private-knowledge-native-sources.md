# Private knowledge: native source and authorization boundary

Status: implementation foundation, not an advertised export capability or a
qualified medium project. The unchanged benchmark requires existing SharePoint,
Confluence and company sign-in, 10,000 documents, independent permission changes,
current citations, fail-closed outages, Australian processing and recovery.

## Architecture decision

Use native, caller-delegated search and live document reads as the first private
retrieval path. Preserve the source systems and their permission authority. Their
existing indexes search the collection; a small ranked result set bounds each model
request. Do not import the old normalized 100-document fixture catalog or claim that
it implements these vendor integrations. A small retrieval result count is not a
limit on the source collection, but 10,000-document relevance, throughput and quota
behavior still require evaluation.

`enterprise_sources.py` implements Microsoft Graph v1.0 drive search, live drive-item
metadata and content download, plus Confluence Cloud CQL search and REST v2 page
reads. All use the authenticated person's delegated access token. `/me` identity
must agree with the trusted broker's source-account mapping. Confluence also checks
the current accessible-resource grant, configured site and read/search scopes.
Neither credentials nor identity mappings may come from chat, model output or a
request-body assertion. Shared service-account crawler credentials are not a
substitute for caller authorization.

Graph content redirects do not carry the Graph bearer token to storage. Only the
configured tenant SharePoint host is admitted for a download; other hosts fail
closed. Metadata/version is checked again after download. A decoder callback must
provide isolated supported PDF/Office/text extraction; it is not implemented by
these source adapters. Confluence CQL uses configured **space keys**, while fetched
page `spaceId` is checked against configured **space IDs**. The server constructs
citation URLs and treats page text as untrusted data.

`enterprise_knowledge.py` searches independent sources concurrently. An unavailable
source invalidates the whole request instead of falling back to restricted cached
content. It selects bounded excerpts, rechecks all document access/version before
model context, validates model citation IDs and exact quotes, then rechecks access
and version before releasing the result. Access evidence and private documents are
not persisted by this coordinator. Revocation consistency is still bounded by the
upstream services and the interval after the final live read; this is not a claim of
an atomic transaction with either source.

Audit callbacks contain outcome/counts, with no prompts, private text, titles,
answers, bearer tokens or capability URLs. The application must supply durable audit
storage and trusted account/request attribution. Unknown model/transport errors are
withheld without exposing their bodies. Quote validation prevents fabricated source
references; it cannot prove every natural-language claim is entailed. Independent
answer-quality and adversarial evaluations remain necessary.

## Evidence and limits

Run `npm run test:enterprise`. Current 34 tests use explicit scripted native-contract
and policy fixtures: pagination, delegated identity mismatch/expiry, foreign redirect
and paging refusal, token stripping, metadata/version change, deletion/revocation,
source outage/recovery, two model access gates, foreign citations/tool fields,
privacy-safe audit/error behavior and HTTP response cleanup/size bounds. No Microsoft
or Atlassian account was contacted. Fixture success does not prove vendor deployment,
real OAuth consent, native permission propagation or throughput.

Primary references reviewed 2026-11-10 (content hashes and retrieval times are recorded
in the associated evidence, with raw documentation retained locally):

- [Graph drive search v1.0](https://learn.microsoft.com/en-us/graph/api/driveitem-search?view=graph-rest-1.0)
- [Graph drive-item metadata](https://learn.microsoft.com/en-us/graph/api/driveitem-get?view=graph-rest-1.0)
- [Graph content download](https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0)
- [Confluence CQL search](https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-search/)
- [Confluence REST v2 pages](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/)
- [Confluence CQL fields](https://developer.atlassian.com/cloud/confluence/cql-fields/)
- [Confluence delegated OAuth](https://developer.atlassian.com/cloud/confluence/oauth-2-3lo-apps/)

## Next implementation dependencies

1. Wire authenticated browser/API routes, company session handling, source consent
   callbacks and CSRF controls. The identity verifier, native OAuth protocol drivers
   and encrypted transactional store now exist; their HTTP/browser composition does
   not. Graph uses MSAL PKCE with `form_post`; callback session/cookie handling must
   support that mode. Atlassian Cloud uses its documented confidential-client flow;
   callback access logs, referrers and error bodies must not expose its code.
2. Connect isolated general-document extraction, actual cloud model transports and
   durable privacy-safe query audit. Add real source HTTP/semantic/volume fixtures.
3. Generate complete native application/infrastructure/Spec Kit on all four clouds,
   including source egress, rate limits, existing secret references, backup/key
   recovery, rotation, monitoring and operator bootstrap/mapping administration.
4. Reconcile source/index/model residency and native account prerequisites. Do not
   assume a global SaaS API endpoint proves Australian processing.
5. Add public generator capabilities only when the composition is implemented, then
   run four actual conversations, exact export checks and held-out cases. Continue
   support-copilot and both hard families; the original 28-project scope is unchanged.

## Company identity and source credential implementation

`enterprise_identity.py` verifies RS256 company API credentials against fixed
operator-owned issuer, audience and JWKS configuration, a delegated API scope and
bounded expiry. ID tokens, application-only roles, wrong audiences/issuers/signatures
and expired credentials do not establish API identity. This initial profile requires
API access tokens of at most one hour; it does not implement SAML, opaque-token
introspection or every possible existing company IdP configuration. Provision an
appropriate API registration/federation using the existing IdP; do not replace it.
The coordinator now also requires a live company-authorization callback at request,
model-context and result-release boundaries.

`enterprise_oauth.py` uses actual MSAL 1.39.0 confidential-client code/cache/refresh
behavior for Graph. Confluence uses native documented 3LO token exchange and rotating
refresh. Source account IDs are compared to operator-controlled mappings. Client
secrets are injected; they are not flow records or model context. Token requests have
bounded timeouts, no environment proxy, no redirects and no automatic HTTP retries.

`enterprise_auth_store.py` binds encrypted material to account, principal, source,
mapping revision and purpose. OAuth state is single-use, expires after five minutes,
and is bound to the company principal and a strong private browser nonce. The broker
role can read membership/mapping authority but cannot write it. Excess inherited
write/ownership privileges are rejected before grants. Raw state and verifier/token
material are not stored in plaintext. Encryption does not conceal the existence or
creation time of records; its key must remain separate from SQL and source control.

A refresh intent commits before any token HTTP call. Concurrent callers see an
in-progress fence. A crash cannot silently expose the previous rotating token for
reuse. Successful results recheck live membership/mapping and use a revision fence;
a late response cannot undo disconnection. An uncertain result clears usable material
and requires a fresh source consent. A stale in-progress refresh becomes reconnection
required instead of replaying the old token. This deliberately favors authorization
and rotation safety over automatic recovery from an uncertain external transaction.
Fresh consent must be presented as a simple source-connection action, not a technical
question for the client. API/browser rendering is still to be implemented.

`npm run test:enterprise:postgres` exercises real owned-loopback SQL with a newly
created restricted broker role. The final 16 tests pass independently on PostgreSQL
17 and 18, including actual MSAL/Confluence protocol drivers connected to the
transactional store with scripted vendor responses. `npm run test:enterprise` passes
34 crypto/native-SDK/contract/policy tests. These commands use the existing local
qualification environments. The new 12-package hash-pinned auth dependency slice
still needs a clean Linux installation/runtime check; it is not installation proof.
No live company IdP, Microsoft or Atlassian account/consent was exercised.

Additional reviewed references:

- [MSAL token acquisition](https://learn.microsoft.com/en-us/entra/msal/python/getting-started/acquiring-tokens)
- [MSAL cache serialization](https://learn.microsoft.com/en-us/entra/msal/python/advanced/msal-python-token-cache-serialization)
- [Fernet 50.0.2](https://cryptography.io/en/50.0.2/fernet/)
- [PyJWT 2.15.1](https://pyjwt.readthedocs.io/en/2.15.1/usage.html)
