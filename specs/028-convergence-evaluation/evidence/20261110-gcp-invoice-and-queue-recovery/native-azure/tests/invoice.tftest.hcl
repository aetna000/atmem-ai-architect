mock_provider "azurerm" {
 override_during = plan
 mock_data "azurerm_client_config" { defaults = { subscription_id="11111111-1111-1111-1111-111111111111",tenant_id="22222222-2222-2222-2222-222222222222",object_id="00000000-0000-4000-8000-000000000001" } }
}
mock_provider "azuread" { override_during = plan }
mock_provider "azapi" { override_during = plan }
override_resource {
 override_during = plan
 target = azurerm_resource_group.block_696e766f696365
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture"}
}
override_resource {
 override_during = plan
 target = azurerm_virtual_network.block_696e766f696365
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Network/virtualNetworks/fixture"}
}
override_resource {
 override_during = plan
 target = azurerm_subnet.block_696e766f696365_apps
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Network/virtualNetworks/fixture/subnets/apps"}
}
override_resource {
 override_during = plan
 target = azurerm_subnet.block_696e766f696365_database
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Network/virtualNetworks/fixture/subnets/database"}
}
override_resource {
 override_during = plan
 target = azurerm_subnet.block_696e766f696365_endpoints
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Network/virtualNetworks/fixture/subnets/endpoints"}
}
override_resource {
 override_during = plan
 target = azurerm_user_assigned_identity.block_696e766f696365_api
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.ManagedIdentity/userAssignedIdentities/api","client_id":"00000000-0000-4000-8000-000000000100","principal_id":"00000000-0000-4000-8000-000000000200"}
}
override_resource {
 override_during = plan
 target = azurerm_user_assigned_identity.block_696e766f696365_worker
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.ManagedIdentity/userAssignedIdentities/worker","client_id":"00000000-0000-4000-8000-000000000101","principal_id":"00000000-0000-4000-8000-000000000201"}
}
override_resource {
 override_during = plan
 target = azurerm_user_assigned_identity.block_696e766f696365_pull
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.ManagedIdentity/userAssignedIdentities/pull","client_id":"00000000-0000-4000-8000-000000000102","principal_id":"00000000-0000-4000-8000-000000000202"}
}
override_resource {
 override_during = plan
 target = azurerm_user_assigned_identity.block_696e766f696365_operator
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.ManagedIdentity/userAssignedIdentities/operator","client_id":"00000000-0000-4000-8000-000000000103","principal_id":"00000000-0000-4000-8000-000000000203"}
}
override_resource {
 override_during = plan
 target = azurerm_private_dns_zone.block_696e766f696365_database
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Network/privateDnsZones/database.example.test"}
}
override_resource {
 override_during = plan
 target = azurerm_private_dns_zone.block_696e766f696365_blob
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Network/privateDnsZones/blob.example.test"}
}
override_resource {
 override_during = plan
 target = azurerm_private_dns_zone.block_696e766f696365_model
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Network/privateDnsZones/model.example.test"}
}
override_resource {
 override_during = plan
 target = azurerm_private_dns_zone.block_696e766f696365_vault
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Network/privateDnsZones/vault.example.test"}
}
override_resource {
 override_during = plan
 target = azurerm_postgresql_flexible_server.block_696e766f696365
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.DBforPostgreSQL/flexibleServers/invoice-fixture","fqdn":"invoice-fixture.postgres.database.azure.com"}
}
override_resource {
 override_during = plan
 target = azurerm_storage_account.block_696e766f696365
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Storage/storageAccounts/invoicefixture"}
}
override_resource {
 override_during = plan
 target = azurerm_storage_container.block_696e766f696365
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Storage/storageAccounts/invoicefixture/blobServices/default/containers/invoices"}
}
override_resource {
 override_during = plan
 target = azurerm_cognitive_account.block_696e766f696365
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.CognitiveServices/accounts/invoice-fixture","endpoint":"https://invoice-fixture.openai.azure.com/"}
}
override_resource {
 override_during = plan
 target = azurerm_key_vault.block_696e766f696365
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.KeyVault/vaults/invoice-fixture","vault_uri":"https://invoice-fixture.vault.azure.net/"}
}
override_resource {
 override_during = plan
 target = azurerm_container_app_environment.block_696e766f696365
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.App/managedEnvironments/invoice-fixture","default_domain":"invoice-fixture.australiaeast.azurecontainerapps.io"}
}
override_resource {
 override_during = plan
 target = azurerm_container_registry.block_696e766f696365
 values = {
 id = "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.ContainerRegistry/registries/fixture"
 login_server = format("invoice%sacr.azurecr.io",substr(sha256("https://atmem.ai/workspaces/11111111-1111-4111-8111-111111111111/block_696e766f696365/staging"),0,12))
 }
}
override_resource {
 override_during = plan
 target = azurerm_role_definition.block_696e766f696365_documents
 values = {"role_definition_resource_id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/invoice-fixture/providers/Microsoft.Authorization/roleDefinitions/00000000-0000-4000-8000-000000000050"}
}
override_resource {
 override_during = plan
 target = azuread_application_registration.block_696e766f696365
 values = {"id":"/applications/00000000-0000-4000-8000-000000000301","client_id":"00000000-0000-4000-8000-000000000401"}
}
override_resource {
 override_during = plan
 target = azuread_service_principal.block_696e766f696365
 values = {"object_id":"00000000-0000-4000-8000-000000000501"}
}
override_resource {
 override_during = plan
 target = azuread_application_registration.block_696e766f696365_spa
 values = {"id":"/applications/00000000-0000-4000-8000-000000000302","client_id":"00000000-0000-4000-8000-000000000402"}
}
override_resource {
 override_during = plan
 target = azuread_service_principal.block_696e766f696365_spa
 values = {"object_id":"00000000-0000-4000-8000-000000000502"}
}
override_resource {
 override_during = plan
 target = azuread_application_registration.block_696e766f696365_parser
 values = {"id":"/applications/00000000-0000-4000-8000-000000000303","client_id":"00000000-0000-4000-8000-000000000403"}
}
override_resource {
 override_during = plan
 target = azuread_service_principal.block_696e766f696365_parser
 values = {"object_id":"00000000-0000-4000-8000-000000000503"}
}

variables {
review_approved = true
applications_enabled = true
region = "australiaeast"
subscription_id = "11111111-1111-1111-1111-111111111111"
tenant_id = "22222222-2222-2222-2222-222222222222"
accounting_endpoint = "https://accounting.example.test/actions"
accounting_scope = "owned-team"
model_name = "REVIEW_MODEL"
model_version = "REVIEW_VERSION"
runtime_image = format("%sacr.azurecr.io/invoice/runtime@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",replace(format("invoice-%s",substr(sha256("https://atmem.ai/workspaces/11111111-1111-4111-8111-111111111111/block_696e766f696365/staging"),0,12)),"-",""))
parser_image = format("%sacr.azurecr.io/invoice/parser@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",replace(format("invoice-%s",substr(sha256("https://atmem.ai/workspaces/11111111-1111-4111-8111-111111111111/block_696e766f696365/staging"),0,12)),"-",""))
staff_subjects = ["55555555-5555-5555-5555-555555555555"]
replay_review_base64 = ""
}
run "private_data_and_parser" {
 command = plan
 assert {
 condition = !azurerm_postgresql_flexible_server.block_696e766f696365.public_network_access_enabled && !azurerm_postgresql_flexible_server.block_696e766f696365.authentication[0].password_auth_enabled && !azurerm_storage_account.block_696e766f696365.public_network_access_enabled && !azurerm_cognitive_account.block_696e766f696365.local_auth_enabled
 error_message = "Private data and keyless database/model boundaries are required."
 }
 assert {
 condition = azapi_resource.block_696e766f696365_parser[0].body.properties.configuration.identitySettings[0].lifecycle == "None" && azapi_resource.block_696e766f696365_parser[0].body.properties.configuration.ingress.external == false
 error_message = "Parser image-pull identity must not be available in the private runtime."
 }
}
run "foundation_only" {
 command = plan
 variables { applications_enabled = false }
 assert {
 condition = length(azapi_resource.block_696e766f696365_api) == 0 && length(azapi_resource.block_696e766f696365_worker) == 0 && length(azapi_resource.block_696e766f696365_parser) == 0
 error_message = "Release must follow bootstrap, secret population and immutable publication."
 }
}
run "separate_workloads_and_regional_model" {
 command = plan
 assert {
 condition = azurerm_user_assigned_identity.block_696e766f696365_api.client_id != azurerm_user_assigned_identity.block_696e766f696365_worker.client_id && azurerm_cognitive_deployment.block_696e766f696365.sku[0].name == "Standard" && azurerm_cognitive_deployment.block_696e766f696365.version_upgrade_option == "NoAutoUpgrade"
 error_message = "Separate identities and an explicit regional model version are required."
 }
 assert {
 condition = one([for entry in azapi_resource.block_696e766f696365_parser[0].body.properties.template.containers[0].env : entry.value if entry.name == "PARSER_AUTH_MODE"]) == "entra-workload" && azuread_application_app_role.block_696e766f696365_parser.value == "Parser.Invoke"
 error_message = "Private ingress alone does not authorize the exact worker."
 }
}
run "mutable_image_rejected" {
 command = plan
 variables { runtime_image = "unreviewed:latest" }
 expect_failures = [var.runtime_image]
}
run "foreign_registry_rejected" {
 command = plan
 variables { runtime_image = "foreign.azurecr.io/invoice/runtime@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
 expect_failures = [terraform_data.review_gate]
}
run "unadmitted_staff_rejected" {
 command = plan
 variables { staff_subjects = [] }
 expect_failures = [terraform_data.review_gate]
}

run "review_required" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
