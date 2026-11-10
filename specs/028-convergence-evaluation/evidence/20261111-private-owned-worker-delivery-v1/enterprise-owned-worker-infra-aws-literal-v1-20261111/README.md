# AWS private parser substrate

Creates a new dedicated private VPC, two subnets, API/ECR/SSM endpoints, temporary no-history S3 store, separate host/transfer/image-pull roles, immutable repositories, fixed host verifier and optional EC2 pool/static task revision. Existing worker identity is referenced by its full ARN and receives additive named policies. No existing pool, database, document source or website is adopted.

Review costs before foundation apply: endpoints incur standing charges even with hosts disabled. Hosts are a fixed bounded standing pool, not automatically scaled or performance-qualified. Supply actual reviewed AMI and independently qualified immutable images; discovery metadata does not approve them. Runtime output remains null until both switches are enabled.

No NAT, internet gateway, public IP or SSH ingress is created. Trusted transfer stages can reach the named private APIs and the S3 gateway prefix list; the parser has networking disabled. Physical erasure, native host/agent/SSM/IAM behavior, strict retention and throughput require destination qualification. One-day lifecycle is an asynchronous fallback, not a deadline.

Task definitions belong to Terraform, not the worker. Upgrade by publishing a new reviewed revision and draining active work before replacing hosts; automatic rolling host replacement/draining is not implemented. Keep the old cleanup target available when changing family/bucket/destination. Never destroy populated stores or terminate active hosts without a reviewed drain.

Complete API/worker/SQL/model/source hosting, enrollment, secrets, recovery and Spec Kit/export composition remain unfinished. No whole-project, security, cloud-plan or deployment acceptance is implied.
