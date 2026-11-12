# Code Engine foundation inputs and ownership

Use the database_bootstrap and operator_deployment outputs, not guessed identifiers.
The new database's built-in application database is ibmclouddb; the separate operator
owns the new workflow schema. Application SQL passwords are distinct strong random
values created outside Terraform. Native trusted profiles authorize COS/model
access, not database login: operator bindings use stable owned credential UUIDs,
not a false claim of native IAM-to-SQL authentication.

In the new Code Engine project, an authorized operator creates these references
from private mode-0600 inputs, without placing secret values in Terraform/state:
- registry_pull_secret: native registry configuration, private namespace pull only.
- databaseConfig config map: exact private host, port and native PEM ca_pem.
- apiSecret generic secret: password for the generated API SQL login only.
- workerSecret generic secret: worker SQL password and existing accounting_token.
- parserSecret generic secret: token, exactly 64 lowercase hexadecimal characters
  from 32 cryptographically random bytes; only worker and parser reference it.

Read native connection/CA metadata for this exact database deployment. Never use a
public hostname or weaken TLS verification to bypass private connectivity. Supply
bootstrap's private operator files and create both nonadministrative logins, exact
schema/grants and memberships. Native CA/token rotation requires an explicit rollout;
rotate parser/worker together and verify old/missing tokens are denied. The parent
parser removes the token from its environment and its native tools use a minimal
explicit environment. This is not an OS sandbox or proof of inherited platform IAM.

The API derives its same-origin policy only from documented Code Engine app/domain/
subdomain/region settings matched to its compiler-owned service name. No request
Host or Forwarded header chooses a trusted origin. The App ID redirect resource
references the created API endpoint after creation, avoiding a Terraform cycle.
