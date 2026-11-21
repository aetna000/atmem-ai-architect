# Implementation plan

1. Add typed principal binding and access mode to shared frontend/server contracts.
2. Compile supported direct operator-to-S3 edges into required inputs and scoped bucket grants.
3. Derive coverage from implemented contracts; retain unsupported gaps and review gates.
4. Update architect guidance and handoff instructions to use the supported capability.
5. Exercise serialization, server contracts, generated policies, Terraform mock plans and live prompting/export; correct failures before continuing.

Constitution: proposals remain reviewable and undoable; no actual ARN/credential guessed; one project model drives outputs; no cloud mutation during local qualification.
