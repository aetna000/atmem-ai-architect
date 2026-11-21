# Local AWS emulation before download

Provide a browser action in Outputs and Terraform that executes server-generated application code against isolated stateful Moto APIs. Use synthetic inputs; never read AWS credentials or make cloud calls. Report generated artifact hashes, checks, emulated capabilities and unverified boundaries. Unsupported/incomplete designs cannot receive a success result. Reset evidence when project/environment changes; allow report download.

Initial backend: Moto 5.2.5 in a short-lived process. Execute handlers directly, never use Moto's Dockerless Lambda success placeholder. S3/SQS/DynamoDB APIs are stateful; Bedrock responses and API-authorizer envelopes are explicit deterministic fixtures. No Terraform apply, IAM enforcement, API Gateway/Cognito/CloudFront lifecycle or real model quality is claimed. Existing provider-schema/mock-plan checks remain separate.

Future hosted deployment: same relative HTTP API and worker request/result contract. Browser never controls filesystem paths or container sockets. Local adapter has a bounded process timeout, single job concurrency, synthetic credential environment, no external network and ephemeral working directory. Public hosting requires independent authentication/tenant authorization, queue admission controls, container/OS isolation, network-deny policy, CPU/memory quotas and scoped evidence storage; local process isolation is not advertised as a hostile multi-tenant sandbox.

Strengthen emulation through versioned capability/probe results and negative tests. A failing production handler must make the emulation fail. An emulator deficiency must be recorded separately; no monkeypatch that merely forces success. Preserve previously archived example evidence.
