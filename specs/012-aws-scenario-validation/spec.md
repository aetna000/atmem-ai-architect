# AWS scenario validation

User request: exercise AtMem AI Architect from ordinary prompting through architecture, generated deployment artifacts, local validation, real AWS testing and product correction for seven progressively complex scenarios.

## Scenario ladder
1. Private object storage.
2. Authenticated document-statistics compute.
3. Reliable asynchronous document processing.
4. Model-backed summarization.
5. Retrieval-augmented answers with citations.
6. Authenticated permission-aware retrieval.
7. External sources and enterprise operation.

## Evidence rules
Run the real application/model path with synthetic data; distinguish it from deterministic regression fixtures. Every stage records prompt, returned architecture, artifact identity, expected and observed checks, blockers and evidence paths. Unsupported generation is blocked, not passed. Native model/account usage is authorized by the user request. AWS provisioning requires a concrete resource plan and agreed account/profile, region and spend boundary. No secret values in artifacts. Existing systems are not modified as test fixtures.

## Acceptance
A supported scenario must generate complete artifacts, pass local checks, produce an account-specific plan, deploy within the approved test scope, pass positive and negative deployed tests, support an update and approved cleanup. Failures must lead to product fixes and fresh evidence. A model's success claim is never a test result.
