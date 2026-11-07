# Decisions

- Use Converse with one direct regional foundation model, supplied explicitly at deployment; no default entitlement or silent cross-region fallback.
- Grant only bedrock:InvokeModel on the selected model ARN. The caller invokes the live Lambda alias through an explicit existing IAM-principal binding.
- SDK attempts are bounded to two. Service errors return sanitized retryability; no input or raw model error enters application logs.
- Default token limit is 512 and input limit 16000 bytes. These are proposed settings, not confirmed business requirements.
- API semantics reviewed: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html .
