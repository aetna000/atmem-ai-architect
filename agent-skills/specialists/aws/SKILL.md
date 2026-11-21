---
name: aws
description: AWS architecture guidance
version: 1.4.0
---

Keep the requested workload scope. Native generation covers S3, typed text-statistics Lambda and asynchronous word-count pipelines and bounded Bedrock summaries and explicitly selected keyword RAG and same-account IAM-principal access; other resources and integrations remain product work. A diagram or regional catalog entry is not deployment evidence. Separate storage, requests, transfer, models, embeddings and vector-store costs; do not invent prices or success probabilities.

Iterate prompt → diagram → exported artifacts → validation findings → product fix → fresh export. Preserve required components and unresolved-work gates. Distinguish diagram corrections from absent generator/application code. Trace identity, data, result and failure paths; verify model IDs, region, quotas, ACLs and external interfaces.

Use one physical service per data.service field. CloudTrail and CloudWatch differ; model invocation and Bedrock Guardrails differ. Do not silently select one from a combined name.

For versioned S3 events, read the event's exact versionId and authorize scoped s3:GetObjectVersion. An idempotency key containing versionId is insufficient if code reads the latest object. For SQS → Lambda, use visibility timeout at least six times function timeout plus batching window; specify partial batch failures and idempotent completion.

Primary references reviewed 2026-11-07:
- https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html
- https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html
