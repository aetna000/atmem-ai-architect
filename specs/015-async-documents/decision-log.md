# Decisions

- 2026-11-07: Use typed, bounded UTF-8 word-count behavior for this scenario. Do not infer arbitrary application code from Lambda labels.
- Pin SDK wheels and transitive dependencies by hash; package deterministically for Python 3.13 ARM64. Keep licenses and package metadata.
- Store one conditional result per bucket/key/version; retryable failures remain failed SQS records. Poison messages use bounded redrive.
- Require reviewed existing SNS alert destinations in production. An empty destination is permitted only for staging qualification.
- Reject shared pipeline resources and overlapping bucket notifications until fan-out semantics have their own implementation and acceptance tests.
- AWS semantics checked against https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html and https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-event-types-and-destinations.html .
