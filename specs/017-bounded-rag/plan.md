# Implementation sequence

1. Implement and test the retrieval/authorization core independently of provider adapters.
2. Implement a trusted AWS authentication adapter; never derive identity or employee region from request-body fields. Prevent direct end-user Lambda invocation from bypassing the gateway.
3. Implement bounded strongly consistent document/ACL storage and authenticated ingestion/update/delete operations.
4. Generate the API, storage, scoped runtime permissions, bounded model calls and operational resources from typed diagram contracts.
5. Run prompt/refinement/export loops for cited RAG and permission-aware RAG, then validate downloaded artifacts.
6. Qualify live access isolation, citations, unknown questions, updates/deletes, revocation and recovery after account prerequisites are satisfied.

External SharePoint/Confluence adapters will first use local contract test servers unless real test tenants are provided. Local tests must never be labelled live connector acceptance.
