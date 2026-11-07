# Authenticated knowledge web application

CloudFront serves private S3 assets and proxies /api/* to the authenticated API. Cognito uses authorization-code flow with S256 PKCE, required software-token MFA and administrator-created users. The API requires the atmem/ask access-token scope; identity and employee region come from the authoritative catalog mapping, never request-body fields or editable profile claims.

Run manage-web-users.py using a separate reviewed operator identity, the output user pool/catalog, exact account and region, an authoritative subject/employee-region mapping and --confirm-change. It prompts for a temporary password, suppresses invitation email and journals the new user before adding the directory mapping. Deliver credentials through your approved secure process; the user sets a permanent password and enrolls MFA at first sign-in. A partial onboarding failure remains denied until its directory mapping is completed. Never add passwords to Terraform or source control.

Disable a user with the same tool and --disable: the authoritative directory is disabled before Cognito, so already-issued tokens lose application access. Review the receipt if either step fails. Existing administrator IAM permissions can bypass application controls; end users must not hold those permissions.

Verify sign-in/MFA, logout, expired/incorrect-scope tokens, Alice/Bob isolation, source citations, document changes and user revocation through the actual web application. Local browser fixtures are not live Cognito acceptance. Frontend tokens stay in memory; transient PKCE state is removed after callback. No external scripts or HTML rendering of model answers are used.
