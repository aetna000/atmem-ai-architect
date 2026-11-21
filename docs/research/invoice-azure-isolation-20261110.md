# Azure invoice parser isolation review

Reviewed 2026-11-10. This guides the next native adapter; it is not cloud
qualification or an implemented Azure invoice deployment. Public source text is
untrusted evidence. Do not copy a source repository into a client handoff.

The current AzureRM 4.81.0 native container-app schema has no identity lifecycle
setting. Microsoft documents an image-pull identity lifecycle of `None`, which
keeps that identity unavailable to running containers. The stable Container Apps
2025-07-01 REST definitions include this setting. This is relevant to pulling our
private parser image while withholding cloud credentials from the PDF processor.
[Microsoft identity guidance](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity)

The maintained Azure Verified Module uses AzAPI and explicitly emits identity
lifecycle settings. Reviewed revision:
`0dc4faf510f8eb7ca6d151e1be6a47fb55a0074b`. Its implementation informs the boundary;
the module has not been adopted. Its preview API is not automatically our choice.
[Pinned module implementation](https://github.com/Azure/terraform-azurerm-avm-res-app-containerapp/blob/0dc4faf510f8eb7ca6d151e1be6a47fb55a0074b/main.tf)

Pinned stable REST source revision:
`5488b1fa09dbafc9714df8af988bb5228b66e3cc`. Configuration references the
CommonDefinitions IdentitySettings type; its lifecycle enum includes None.
[Container Apps definition](https://github.com/Azure/azure-rest-api-specs/blob/5488b1fa09dbafc9714df8af988bb5228b66e3cc/specification/app/resource-manager/Microsoft.App/ContainerApps/stable/2025-07-01/ContainerApps.json),
[common definitions](https://github.com/Azure/azure-rest-api-specs/blob/5488b1fa09dbafc9714df8af988bb5228b66e3cc/specification/app/resource-manager/Microsoft.App/ContainerApps/stable/2025-07-01/CommonDefinitions.json).

AzAPI 2.13.0 was initialized locally through the Terraform registry and its native
resource schema inspected. No cloud credentials or account operations were used.
Review material, exact hashes, initialization log, provider lock and schema are in
`.local/invoice-azure-review`; a provider download alone proves no Azure behavior.
The initial REST download used an incorrect repository path and returned HTTP404;
the corrected pinned path above was fetched and checked independently.

Private environment ingress alone does not distinguish the worker from another
application in that environment. Also, an authenticated service token is not
authorization: Microsoft's service-to-service guidance requires the target code to
validate the intended role. Do not assume Easy Auth checks our app-role contract.
[Microsoft service authentication guidance](https://learn.microsoft.com/en-us/azure/container-apps/authentication-entra)

Next implementation candidate: Container Apps with separate API/worker identities,
an image-pull-only parser identity whose lifecycle is None, private parser ingress
and a fixed worker-to-parser Entra app-only contract. Implement and test exact
tenant/audience/worker principal/application-role checks, including signature,
expiry, wrong-caller and delegated-token denial. The existing parser client/server
do not yet implement that Azure contract; add it at the generator/runtime source.
Keep the parser free of database, object-store, model and accounting authority.

Complete the associated native private PostgreSQL, storage, model, secret and
operator-job resources, then independently check emitted source, provider schemas,
positive/negative plans, actual images and a complete client-brief export. Preserve
the Australia placement and existing accounting system. Do not count this review
as an invoice benchmark pass or replace the four-provider goal with a parser demo.
