# Decisions

- 2026-11-07: User approved bounded keyword retrieval as the first end-to-end target; managed vector retrieval remains a separate later qualification. User approved local connector test servers for this stage; real external tenant deployment remains unverified.
- Authorization precedes relevance scoring; denied metadata is omitted from evidence and citations.
- Recheck evidence before generation and delivery. Revocation during model processing suppresses response delivery, but cannot retract evidence already sent while authorized; this timing limit must be explicit in deployed acceptance.
- No cached answers until permission-aware invalidation has its own implementation and tests.
- Local pure-core tests do not complete cloud infrastructure, authentication or model-quality qualification.
