# AtMem Architecture Review

Check infrastructure plans against team policy before an agent turns them into implementation tasks.

Local development candidate. No public package, catalog listing or hosted service is claimed. The supplied [PLAN.md](PLAN.md) is the original proposal; [current evidence](../specs/033-architecture-review-hook/) records what actually runs.

## Install locally

Python 3.11+:

```sh
python3 -m venv .review-venv
.review-venv/bin/python -m pip install ./atmem-review-hook
.review-venv/bin/atmem-review atmem-review-hook/examples/review-input.sample.json
```

Exit 1 is the expected sample verdict: wrong region, public RDS and world-open database ingress. There is no fabricated monthly price.

For MCP, configure server **atmem-architect** with the installed `atmem-review-mcp` executable. It exposes exactly one tool, `review_plan`. Send artifact and policy contents; paths are citation labels, never server file-access requests. STDIO emits protocol messages only.

Codex CLI setup, using an absolute installed executable path:

```sh
codex mcp add atmem-architect -- /absolute/path/.review-venv/bin/atmem-review-mcp
codex mcp list
```

See [official Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli). Other clients can use this stdio configuration:

```json
{"mcpServers":{"atmem-architect":{"command":"/absolute/path/.review-venv/bin/atmem-review-mcp","args":[]}}}
```

## Workflow integrations

- [Spec Kit extension](spec-kit/README.md): mandatory `before_tasks`, optional `after_plan`; locally installed/tested with Spec Kit 1.0.4.
- [OpenSpec schema](openspec/schemas/atmem-reviewed/schema.yaml): review artifact precedes tasks. A fail writes `review.blocked.md`, not `review.md`.

These are agent instructions and artifact dependencies, not an unbypassable security boundary. Missing rules or reviewer availability are WARN. Use strict fresh CI review when unknowns must stop a build.

## Fresh CI gate

```sh
atmem-review-ci --root . --rules architecture.md \
  --artifact plan:specs/example/plan.md \
  --terraform-plan infra/tfplan.json --strict
```

CI rebuilds its request from current explicitly selected files. A hand-edited or stale `architecture-review.json` is not an input. Exit 0 means no blocking verdict, 1 means policy failure, and 2 means missing/invalid input. Reports include a SHA-256 binding of the actual normalized request. The reviewer does not generate the Terraform plan.

## Coverage

| Policy | Implemented evidence | Explicit limits |
|---|---|---|
| Attribute predicates | Resource type, dotted attribute and exact required value | Missing/computed/sensitive values unverified |
| Regions | Known resource region or constant provider region, including module/provider aliases | Variable expressions and unmapped provider bindings unverified |
| Public ingress | AWS inline/standalone SG ingress, IPv4/IPv6, proven ALB TCP 443 exception | Unknown ports/associations/topology unverified |
| Services | Explicit forbidden types and mapped compute/database/storage/queue allowlists | Unmapped categories unverified |
| Residency | Explicit `atmem:data_classes` tags and known AWS country mappings | No invented data classification; backup/log/global replication coverage unverified |
| Uptime | Inspectable single-AZ RDS finding | No configuration proves an uptime percentage |
| Budget | Matching-currency, complete cost adapter output | Missing/unsupported/partial prices remain unverified |
| Prose/ADRs | Optional model suggestions with independently checked exact line citations | Model consistency is advisory; no deployment proof or override of deterministic findings |

Only the supplied state is reviewed. Changes-only/deferred plans do not prove unchanged estate coverage. Valid expiring exceptions retain the finding and waiver identity. Unknown YAML fields/aliases and oversized input are rejected. JSON is bounded to 16 MB, 64 artifacts, 200 rules and 10,000 resources; contents are never silently truncated.

## Optional external adapters

Default: **no pricing/model network calls**. MCP/CLI startup must explicitly enable each adapter.

- Cost: `--allow-cost-egress`, installed `infracost`, and `INFRACOST_CLI_AUTHENTICATION_TOKEN` in the server environment. The fixed command is `infracost scan <private-temp-plan.json> --json --currency <ISO>`. Its fresh temporary home receives no cloud credentials. The current CLI command/flags were checked against checksum-verified Infracost CLI 2.19.1. Its versioned source defines the accepted scan output; legacy JSON v0.2 is also recognized. Unsupported/missing prices fail closed. One real EC2/gp3 plan is now qualified with under/over-budget decisions ([evidence](../specs/033-architecture-review-hook/evidence/live-pricing.json)); broader resource/provider/currency coverage remains unqualified. The runtime does not read interactive login caches; automation supplies its own supported token. See [Infracost CLI documentation](https://www.infracost.io/docs/features/cli_commands/).
- Prose: `--allow-model-egress`, `ATMEM_REVIEW_OPENROUTER_MODEL` and `ATMEM_REVIEW_OPENROUTER_API_KEY`. Only the bounded selected prose/rules are sent to the configured model, with no tools or Terraform plan JSON. Pattern filtering blocks detected secrets; it cannot establish arbitrary text is secret-free. Live model quality/usage is unqualified until separately tested.

The core and MCP never modify customer artifacts. An explicitly enabled cost adapter uses a private ephemeral directory, removed after invocation. The local CLI/CI wrapper reads only caller-selected files; report persistence is the caller's stdout redirection.

## Test and rollback

```sh
PYTHONPATH=atmem-review-hook/src python -m unittest discover -s atmem-review-hook/tests -v
```

Disable/remove the Spec Kit extension or select the previous OpenSpec schema to stop the prompt gate. Remove the MCP server to stop local tool execution. Existing source, infrastructure, state and cloud accounts remain untouched. No generated files or account resources need rollback.
