# Owned AWS parser-host verification

This module creates one fixed, parameterless SSM command and appends one named policy to the existing question worker. It references the selected existing parser cluster. It does not create a compute pool, replace a worker role, deploy an application or register a complete private capability.

Only this SSM document may be submitted, and only instances tagged with the exact policy fingerprint may be targeted. The worker pins native document version/hash, independently checks command content and restricts task placement to the instances it just verified. GetCommandInvocation requires resource wildcard in the native IAM contract; no command discovery, document mutation or Parameter Store read is granted. Account inherited permissions still require inspection.

Provision the dedicated private host pool with matching ECS/daemon/IMDS settings and tags before use. This module deliberately emits no ready parser configuration or invented image/AMI. Runtime/identity, host drift, IAM and eventual native behavior remain subject to independent destination qualification. No account plan or deployment has run.
