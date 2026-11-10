mock_provider "azurerm" {
 override_during = plan
 mock_data "azurerm_client_config" { defaults = { subscription_id = "11111111-1111-1111-1111-111111111111", tenant_id = "22222222-2222-2222-2222-222222222222" } }
}
override_resource {
 override_during = plan
 target = azurerm_user_assigned_identity.block_6661712d617070
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/reviewed-applications/providers/Microsoft.ManagedIdentity/userAssignedIdentities/mock-runtime-0","client_id":"00000000-0000-4000-8000-000000000100","principal_id":"00000000-0000-4000-8000-000000000101"}
}
override_resource {
 override_during = plan
 target = azurerm_service_plan.block_6661712d617070
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/reviewed-applications/providers/Microsoft.Web/serverFarms/mock-plan-0"}
}
override_resource {
 override_during = plan
 target = azurerm_cognitive_account.block_6661712d617070
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/reviewed-applications/providers/Microsoft.CognitiveServices/accounts/mock-ai-0","endpoint":"https://mock-ai-0.openai.azure.com/"}
}
override_resource {
 override_during = plan
 target = azurerm_storage_account.block_6661712d617070
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/reviewed-applications/providers/Microsoft.Storage/storageAccounts/mockstorage0"}
}
override_resource {
 override_during = plan
 target = azurerm_storage_container.block_6661712d617070
 values = {"id":"/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/reviewed-applications/providers/Microsoft.Storage/storageAccounts/mockstorage0/blobServices/default/containers/public-catalog"}
}

variables {
review_approved = true
subscription_id = "11111111-1111-1111-1111-111111111111"
tenant_id = "22222222-2222-2222-2222-222222222222"
resource_group_name = "reviewed-applications"
registry_name = "reviewedregistry"
registry_resource_group_name = "reviewed-registry-rg"
block_6661712d617070_name = "reviewed-public-help"
block_6661712d617070_region = "australiaeast"
block_6661712d617070_repository = "architect/public-help"
block_6661712d617070_image_digest = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
block_6661712d617070_model_name = "REVIEW_MODEL"
block_6661712d617070_model_version = "REVIEW_VERSION"
block_6661712d617070_editor_group_object_id = "33333333-3333-3333-3333-333333333333"
}
run "block_6661712d617070_public_boundary" {
 command = plan
 assert {
 condition = azurerm_storage_container.block_6661712d617070.container_access_type == "private" && !azurerm_storage_account.block_6661712d617070.shared_access_key_enabled && !azurerm_storage_account.block_6661712d617070.allow_nested_items_to_be_public
 error_message = "Public answers must not make the object store public or enable storage keys."
 }
 assert {
 condition = azurerm_role_assignment.block_6661712d617070_catalog.role_definition_name == "Storage Blob Data Reader" && azurerm_role_assignment.block_6661712d617070_editor.role_definition_name == "Storage Blob Data Contributor" && azurerm_role_assignment.block_6661712d617070_catalog.principal_id != azurerm_role_assignment.block_6661712d617070_editor.principal_id
 error_message = "Runtime read and authorized editor write identities must remain separate."
 }
 assert {
 condition = azurerm_linux_web_app.block_6661712d617070.https_only && !azurerm_cognitive_account.block_6661712d617070.local_auth_enabled
 error_message = "TLS and workload identity are required."
 }
}
run "block_6661712d617070_mutable_image_blocked" {
 command = plan
 variables { block_6661712d617070_image_digest = "latest" }
 expect_failures = [var.block_6661712d617070_image_digest]
}
run "unapproved_blocked" {
 command = plan
 variables { review_approved = false }
 expect_failures = [terraform_data.review_gate]
}
