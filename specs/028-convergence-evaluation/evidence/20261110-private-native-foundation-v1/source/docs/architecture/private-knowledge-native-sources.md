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

Run `npm run test:enterprise`. Current 23 tests use explicit scripted native-contract
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

1. Implement company identity verification and secure per-person OAuth brokering,
   token refresh/revocation and protected account mappings. Preserve existing sign-in.
2. Connect isolated general-document extraction, actual cloud model transports and
   durable privacy-safe audit. Add real HTTP transport and semantic/volume fixtures.
3. Generate a complete native application/infrastructure/Spec Kit on all four clouds,
   including source egress, rate limits, secret boundaries, monitoring and recovery.
4. Explicitly reconcile source/index/model residency and native account prerequisites;
   do not assume a global SaaS API endpoint proves Australian processing.
5. Add generator skills/capabilities only when the composition is implemented, then
   run four actual conversations, exact export checks and held-out cases. Continue
   support-copilot and both hard families; the original 28-project scope is unchanged.
