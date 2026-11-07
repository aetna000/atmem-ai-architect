# Bounded permission-aware retrieval qualification

User-approved first test target: deterministic keyword retrieval over at most 100 small documents, with versioned citations. This is an explicit small-collection test mode, not an implicit replacement for managed vector retrieval.

Filter authoritative subject and employee-region permissions before examining or ranking document content. Unknown identity and lookup failures fail closed. Recheck strongly consistent content revisions and permissions immediately before model generation and before response delivery. Do not cache responses across permission changes. Unsupported questions must abstain without a model call. Reject citations outside the retrieved evidence.

A model citation contract cannot prove factual correctness. Live quality, adversarial prompts, updates/deletes, revocation timing, authenticated identity propagation and deployed recovery require independent tests.
