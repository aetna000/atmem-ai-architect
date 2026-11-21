# IBM Code Engine container footprint

A native deployment footprint for an explicitly selected, supplied Linux application image listening on port 8080. Pin and build the real application image before use. This compiler does not implement application authentication, payments, durable memory or unspecified connections. It never packages the local loopback sidecar as a hosted application.

Ingress is private; public website routing and user authentication are separate contracts. Runtime identity has no application-data grants. Existing network/environment/project prerequisites must be reviewed; image-pull and platform logging configuration must be verified for the destination. Azure and IBM private-registry credentials require a separate secret integration. No credentials belong in this directory.

Use Terraform 1.7+, copy deployment.tfvars.json.example to a private inputs file, supply every reviewed input and image digest, run terraform init -backend=false, terraform validate and terraform test. Mock tests inspect configuration only. An authorized account plan, real image startup checks, access tests, rollback and approval are required before deployment. Production remains blocked pending state and operational review.
