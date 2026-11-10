# Questions and assumptions to resolve

Snapshot 9e56b56c-f354-4d86-9089-eba95a5c71e8 · design r4 · generated 2026-11-09T23:57:26.530Z

- [ai-public-source-boundary] Confirm REQ-002: The assistant must use only the approved public-help-article catalog for retrieval and answer grounding, with no private-source ingestion or arbitrary URL retrieval.
- [ai-supported-answer-or-abstain] Confirm REQ-003: When current approved articles do not adequately support an answer, the assistant must explicitly say it does not know rather than provide an unsupported answer.
- [ai-article-lifecycle] Confirm REQ-004: Authorized editors must be able to publish, update and remove public articles through a separate management interface; conflicting edits must be rejected and answers must be withheld if their supporting sources change during processing.
- [ai-location-transparency] Confirm REQ-005: Prefer Australian application hosting, article storage and model processing. Before enabling inference, document the selected model deployment's processing geography, retention, logging and recovery locations, identify unverified limitations, and present any proposed processing outside Australia for review. The preference must not be represented as confirmed Australian-only residency.
- [ai-public-access-editor-boundary] Confirm REQ-006: Visitors must be able to ask questions without signing in; only an authorized editor may publish, update or remove catalog articles through the separate management interface.
- [ai-faq-capacity] Confirm REQ-007: The application must support the expected workload of approximately 1,000 questions daily and five simultaneous questions, subject to artifact-bound load tests and verified model quotas; excess concurrency must receive controlled overload handling.
- [ai-faq-file-ingestion] Confirm REQ-008: The editor workflow must accept the twenty supplied public UTF-8 article files, validate each against the implementation's exact 30000-byte limit, and reject invalid or oversized files explicitly without silent truncation.
- [acceptance-req-badd4a62] Agree a measurable acceptance check for REQ-001: Every answer shows its sources
- [acceptance-ai-public-source-boundary] Agree a measurable acceptance check for REQ-002: The assistant must use only the approved public-help-article catalog for retrieval and answer grounding, with no private-source ingestion or arbitrary URL retrieval.
- [acceptance-ai-supported-answer-or-abstain] Agree a measurable acceptance check for REQ-003: When current approved articles do not adequately support an answer, the assistant must explicitly say it does not know rather than provide an unsupported answer.
- [acceptance-ai-article-lifecycle] Agree a measurable acceptance check for REQ-004: Authorized editors must be able to publish, update and remove public articles through a separate management interface; conflicting edits must be rejected and answers must be withheld if their supporting sources change during processing.
- [acceptance-ai-location-transparency] Agree a measurable acceptance check for REQ-005: Prefer Australian application hosting, article storage and model processing. Before enabling inference, document the selected model deployment's processing geography, retention, logging and recovery locations, identify unverified limitations, and present any proposed processing outside Australia for review. The preference must not be represented as confirmed Australian-only residency.
- [acceptance-ai-public-access-editor-boundary] Agree a measurable acceptance check for REQ-006: Visitors must be able to ask questions without signing in; only an authorized editor may publish, update or remove catalog articles through the separate management interface.
- [acceptance-ai-faq-file-ingestion] Agree a measurable acceptance check for REQ-008: The editor workflow must accept the twenty supplied public UTF-8 article files, validate each against the implementation's exact 30000-byte limit, and reject invalid or oversized files explicitly without silent truncation.
- [data.country] Confirm the country and data-residency boundary, including sources, logs and model processing.
- [cloud.region] Engineering verification: choose and document a suitable proposed region within the accepted country, then verify service/model support, residency, quota and account policy before deployment. Escalate only a material business trade-off.
- [scope-boundary] No explicit scope boundary is recorded. Record included and excluded use cases before sizing or implementation.
- [requirement-proposed-61692d61727469636c652d6c6966656379636c65] REQ-004 remains proposed. Confirm, revise or explicitly defer this requirement; do not promote it through generation.
- [requirement-proposed-61692d6661712d6361706163697479] REQ-007 remains proposed. Confirm, revise or explicitly defer this requirement; do not promote it through generation.
- [requirement-proposed-61692d6661712d66696c652d696e67657374696f6e] REQ-008 remains proposed. Confirm, revise or explicitly defer this requirement; do not promote it through generation.
- [requirement-proposed-61692d6c6f636174696f6e2d7472616e73706172656e6379] REQ-005 remains proposed. Confirm, revise or explicitly defer this requirement; do not promote it through generation.
- [requirement-proposed-61692d7075626c69632d6163636573732d656469746f722d626f756e64617279] REQ-006 remains proposed. Confirm, revise or explicitly defer this requirement; do not promote it through generation.
- [requirement-proposed-61692d7075626c69632d736f757263652d626f756e64617279] REQ-002 remains proposed. Confirm, revise or explicitly defer this requirement; do not promote it through generation.
- [requirement-proposed-61692d737570706f727465642d616e737765722d6f722d6162737461696e] REQ-003 remains proposed. Confirm, revise or explicitly defer this requirement; do not promote it through generation.

## Assumptions requiring verification

None recorded.

Also confirm target repository, runtime/toolchain, deployment account owner, access boundaries and release authorization. Ask questions conversationally, starting with those that block the next task.
