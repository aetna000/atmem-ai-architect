# AWS static task ownership checkpoint

The worker consumes an exact active task-definition revision and sends only per-file
transfer environment overrides. It cannot register, list, deregister or delete task
definitions. Configuration v2 replaces the unreleased dynamic-registration prototype.
The task family binds recovery while revision upgrades preserve its cleanup target.
No complete private capability or production worker has been promoted.

The final exact image passes 95 policy, 30 document and 16 host contracts, plus 88
SQL checks on each PostgreSQL 17/18. Installed recovery adds three actual SQL/process-
death checks and eight offline native checks per version; two actual Terraform
command documents are consumed by the installed runtime. The Office/scanned-PDF
pipeline passes 20 checks. Terraform has 14 native provider-mock plans and independent
positive-output checks. JavaScript has 359 tests. Host preparation has 12 local
contracts (real filesystem, simulated daemon/firewall), while separate native Linux
IPv4/IPv6 tests create/remove only temporary unlinked chains. ECS/S3/SSM responses
remain explicit fixtures. No account plans, host deployment, physical-deletion SLA,
whole-project qualification or current-image vulnerability scan is claimed.

Retained failures include the original probe rejecting native option ordering and
the initial grammar qualifier assuming a VM-mounted source path. The latter was
fixed by supplying hash-checked stdlib source directly to the owned VM process.

Reproduce using the qualify-enterprise-runtime, qualify-enterprise-aws-jobs,
qualify-enterprise-aws-recovery, qualify-enterprise-aws-host-infrastructure and
verify-aws-host-configuration scripts with fresh .local evidence directories.
Run tests/runtime/enterprise_aws_bootstrap_contract.py and the native grammar script
qualify-enterprise-aws-firewall-rules.py separately. Use the existing owned Docker
socket; no cloud credentials or deployment are needed.
