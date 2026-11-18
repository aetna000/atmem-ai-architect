<!-- specs/001-taskify/plan.md (excerpt) — produced by /speckit.plan for the Taskify quickstart example,
     with the user asking: "Use .NET Aspire with Postgres ... deploy on AWS with Terraform". -->
## Technical Context

**Language/Version**: C# / .NET 9 (Aspire)
**Primary Dependencies**: Blazor Server, SignalR, EF Core
**Storage**: PostgreSQL 16 on Amazon RDS
**Target Platform**: AWS ECS Fargate behind an ALB
**Performance Goals**: real-time board updates < 500 ms

## Deployment

- Region: `us-east-1` (widest instance availability)
- RDS `db.r6g.xlarge`, Multi-AZ, 500 GB gp3, so reporting tools can connect directly
  the instance is created with `publicly_accessible = true` and a security group allowing 5432 from 0.0.0.0/0
- ECS service: 2 tasks, 1 vCPU / 2 GB each

## Constitution Check

- Security-First: inputs validated ✅
- Microservices: projects, tasks, notifications services ✅
