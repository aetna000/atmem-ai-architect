---
# architecture.md — machine-checked rules for the AtMem reviewer.
# The YAML front matter is the contract; the markdown below is the human record (ADRs).
# spec-kit default path: .specify/memory/architecture.md   OpenSpec default path: openspec/architecture.md
schema: atmem-architecture/v1
project: taskify
owner: platform@taskify.example

budget:
  - id: BUDGET-001
    monthly_max: 150          # hard ceiling for the whole environment
    currency: USD
    environment: production
    severity: error
    warn_at_percent: 80       # warning when estimate >= 80% of max

regions:
  - id: REGION-001
    allowed: [ap-southeast-2]           # Sydney
    severity: error

data_residency:
  - id: RESIDENCY-001
    data_classes: [customer_pii]
    must_stay_in: [AU]
    applies_to: [databases, object_storage, backups, logs]
    severity: error

uptime:
  - id: UPTIME-001
    target_percent: 99.5
    requires: "No single-AZ stateful component unless an exception is recorded"
    severity: warning

services:
  - id: SVC-001
    approved:
      compute: [aws_ecs_service, aws_lambda_function]
      database: [aws_db_instance]          # Postgres on RDS only
      storage: [aws_s3_bucket]
      queue: [aws_sqs_queue]
    forbidden: [aws_instance]             # no hand-managed EC2
    severity: error

network:
  - id: NET-001
    rule: "Databases must not be publicly accessible"
    check: { resource: aws_db_instance, attribute: publicly_accessible, must_equal: false }
    severity: error
  - id: NET-002
    rule: "No security group ingress from 0.0.0.0/0 except to the load balancer on 443"
    severity: error

exceptions: []
#  - id: EXC-001
#    rule_id: UPTIME-001
#    reason: "Single-AZ RDS accepted for the pilot until 2027-03-01"
#    approved_by: javad
#    expires: 2027-03-01
---

# Architecture decisions

## ADR-0001: Postgres on RDS is the only system of record
- Status: Accepted (2026-09-02)
- Decision: All persistent relational data lives in one RDS Postgres instance per environment. No self-managed databases, no second database engine without a new ADR.
- Consequences: Plans that introduce MongoDB, DynamoDB tables for core entities, or Postgres on EC2 violate this ADR.

## ADR-0002: Private networking by default
- Status: Accepted (2026-09-02)
- Decision: Only the public ALB has a public endpoint. Databases, caches and services sit in private subnets and are reached through the VPC.

## ADR-0003: Real-time updates via managed WebSockets, not a self-hosted broker
- Status: Accepted (2026-10-14)
- Decision: Use API Gateway WebSockets (or the app framework's built-in hub behind the ALB). Do not run Redis/RabbitMQ just for fan-out.
- Supersedes: none
