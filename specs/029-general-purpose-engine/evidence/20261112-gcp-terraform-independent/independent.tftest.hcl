mock_provider "google" {
  override_during = plan
}
mock_provider "google-beta" {
  override_during = plan
}
override_data {
  target          = data.google_project.existing
  override_during = plan
  values          = { "number" = "987654321098" }
}
override_resource {
  target          = google_sql_database_instance.owned
  override_during = plan
  values          = { "connection_name" = "independent-local-project:australia-southeast1:independent-samples-pg17" }
}
override_resource {
  target          = google_service_account.runtime["api"]
  override_during = plan
  values          = { "email" = "independent-samples-api@independent-local-project.iam.gserviceaccount.com" }
}
override_resource {
  target          = google_service_account.runtime["worker"]
  override_during = plan
  values          = { "email" = "independent-samples-worker@independent-local-project.iam.gserviceaccount.com" }
}
override_resource {
  target          = google_project_service_identity.iap
  override_during = plan
  values          = { "email" = "service-987654321098@gcp-sa-iap.iam.gserviceaccount.com" }
}
override_resource {
  target          = google_secret_manager_secret.configuration
  override_during = plan
  values          = { "id" = "projects/independent-local-project/secrets/independent-samples-config" }
}
override_resource {
  target          = google_secret_manager_secret.trust
  override_during = plan
  values          = { "id" = "projects/independent-local-project/secrets/independent-samples-trust" }
}
override_resource {
  target          = google_secret_manager_secret.destination_token
  override_during = plan
  values          = { "id" = "projects/independent-local-project/secrets/independent-samples-destination-token" }
}
override_resource {
  target          = google_secret_manager_secret_version.configuration
  override_during = plan
  values          = { "name" = "projects/independent-local-project/secrets/independent-samples-config/versions/1", "version" = "1" }
}
override_resource {
  target          = google_secret_manager_secret_version.trust
  override_during = plan
  values          = { "name" = "projects/independent-local-project/secrets/independent-samples-trust/versions/1", "version" = "1" }
}
variables {
  project_id                = "independent-local-project"
  project_number            = "987654321098"
  workforce_group_email     = "receivers@independent.example.test"
  account_id                = "70000000-0000-4000-8000-000000000001"
  name                      = "independent-samples"
  application_image         = "offline.invalid/review/app@sha256:3333333333333333333333333333333333333333333333333333333333333333"
  sql_proxy_image           = "offline.invalid/review/proxy@sha256:4444444444444444444444444444444444444444444444444444444444444444"
  worker_os_image           = "projects/cos-cloud/global/images/cos-independent-review"
  destination_url           = "https://independent.example.test/route"
  destination_scope         = "independent-review"
  destination_ca_pem        = "-----BEGIN CERTIFICATE-----\nINDEPENDENT-MOCK-NOT-A-REAL-CERTIFICATE\n-----END CERTIFICATE-----"
  destination_token_version = "7"
  migration_password        = "synthetic-independent-write-only-password-0000"
}
run "independent_provisioning_contract" {
  command = plan
  assert {
    condition     = google_cloud_run_v2_service.api.location == "australia-southeast1" && google_sql_database_instance.owned.region == "australia-southeast1" && google_compute_instance_template.worker.region == "australia-southeast1"
    error_message = "Sydney placement across actual delivery units"
  }
  assert {
    condition     = google_cloud_run_v2_service.api.iap_enabled && !google_cloud_run_v2_service.api.invoker_iam_disabled && google_cloud_run_v2_service_iam_member.iap_invoker.role == "roles/run.invoker" && google_cloud_run_v2_service_iam_member.iap_invoker.member == "serviceAccount:${google_project_service_identity.iap.email}"
    error_message = "Native IAP service identity owns invoker grant"
  }
  assert {
    condition     = google_iap_web_cloud_run_service_iam_member.workforce.member == "group:${var.workforce_group_email}" && google_iap_web_cloud_run_service_iam_member.workforce.cloud_run_service_name == google_cloud_run_v2_service.api.name
    error_message = "Existing workforce group resource-scoped access"
  }
  assert {
    condition     = google_cloud_run_v2_service.api.template[0].service_account == google_service_account.runtime["api"].email && google_compute_instance_template.worker.service_account[0].email == google_service_account.runtime["worker"].email && google_service_account.runtime["api"].email != google_service_account.runtime["worker"].email
    error_message = "Separate API/worker identities wired to actual units"
  }
  assert {
    condition     = google_sql_user.runtime["api"].name == trimsuffix(google_service_account.runtime["api"].email, ".gserviceaccount.com") && google_sql_user.runtime["worker"].type == "CLOUD_IAM_SERVICE_ACCOUNT"
    error_message = "Workload SQL IAM user mapping"
  }
  assert {
    condition     = google_sql_database_instance.owned.database_version == "POSTGRES_17" && !google_sql_database_instance.owned.settings[0].ip_configuration[0].ipv4_enabled && google_sql_database_instance.owned.settings[0].ip_configuration[0].ssl_mode == "ENCRYPTED_ONLY"
    error_message = "Private encrypted PostgreSQL17"
  }
  assert {
    condition     = google_sql_database_instance.owned.settings[0].backup_configuration[0].point_in_time_recovery_enabled && google_sql_database_instance.owned.settings[0].backup_configuration[0].enabled && google_sql_database_instance.owned.deletion_protection && google_sql_database_instance.owned.settings[0].deletion_protection_enabled
    error_message = "Recovery and deletion protections retained"
  }
  assert {
    condition     = google_secret_manager_secret_iam_member.worker_token.secret_id == google_secret_manager_secret.destination_token.id && google_secret_manager_secret_iam_member.worker_token.member == "serviceAccount:${google_service_account.runtime["worker"].email}" && google_secret_manager_secret_iam_member.worker_token.member != "serviceAccount:${google_service_account.runtime["api"].email}"
    error_message = "Destination token access belongs to worker"
  }
  assert {
    condition     = alltrue([for key, grant in google_secret_manager_secret_iam_member.config_access : grant.secret_id == google_secret_manager_secret.configuration.id && grant.member == "serviceAccount:${google_service_account.runtime[key].email}"]) && google_secret_manager_secret_iam_member.worker_trust.member == "serviceAccount:${google_service_account.runtime["worker"].email}"
    error_message = "Exact configuration/trust identity wiring"
  }
  assert {
    condition     = jsondecode(google_secret_manager_secret_version.configuration.secret_data).accountId == var.account_id && jsondecode(google_secret_manager_secret_version.configuration.secret_data).destination == var.destination_url && jsondecode(google_secret_manager_secret_version.configuration.secret_data).destinationCaSha256 == sha256(var.destination_ca_pem)
    error_message = "Runtime account destination and CA hash preserve operator values"
  }
  assert {
    condition     = one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "api"]).command == tolist(["/usr/local/bin/python3", "-I", "/app/sample_entry.py"]) && one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "api"]).image == var.application_image && contains(one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "api"]).depends_on, "sql-proxy")
    error_message = "Actual application entrypoint and dependency ordering"
  }
  assert {
    condition     = one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "sql-proxy"]).image == var.sql_proxy_image && contains(one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "sql-proxy"]).args, "--auto-iam-authn") && contains(one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "sql-proxy"]).args, "--private-ip") && contains(one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "sql-proxy"]).args, google_sql_database_instance.owned.connection_name)
    error_message = "SQL proxy native identity/private target wiring"
  }
  assert {
    condition     = one([for e in one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "api"]).env : e if e.name == "DATABASE_SERVICE_ACCOUNT"]).value == google_service_account.runtime["api"].email && one([for e in one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "api"]).env : e if e.name == "DATABASE_NAME"]).value == google_sql_database.application.name
    error_message = "Actual API database identity/name configuration"
  }
  assert {
    condition     = length(google_compute_instance_template.worker.network_interface[0].access_config) == 0 && google_compute_instance_template.worker.shielded_instance_config[0].enable_secure_boot && google_compute_instance_template.worker.disk[0].source_image == var.worker_os_image
    error_message = "Private worker and exact reviewed OS input"
  }
  assert {
    condition     = strcontains(google_compute_instance_template.worker.metadata_startup_script, "--user 10001:10001 --cap-drop ALL --security-opt no-new-privileges") && strcontains(google_compute_instance_template.worker.metadata_startup_script, "TOKEN_VERSION=${google_secret_manager_secret.destination_token.id}/versions/${var.destination_token_version}") && strcontains(google_compute_instance_template.worker.metadata_startup_script, "DATABASE_SERVICE_ACCOUNT=${google_service_account.runtime["worker"].email}")
    error_message = "Rendered worker preserves user/capabilities/scoped credential version and SQL identity"
  }
  assert {
    condition     = google_compute_region_instance_group_manager.worker.target_size == 0 && one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "api"]).args[0] == "provisioning"
    error_message = "Admission is required before worker/application activation"
  }
}
run "independent_activation_contract" {
  command = plan
  variables {
    enable_application = true
    public_origin      = "https://independent-native.run.app"
  }
  assert {
    condition     = google_compute_region_instance_group_manager.worker.target_size == 1 && one([for c in google_cloud_run_v2_service.api.template[0].containers : c if c.name == "api"]).args[0] == "api"
    error_message = "Activation starts API and exactly one worker"
  }
  assert {
    condition     = output.iap_audience == "/projects/${var.project_number}/locations/australia-southeast1/services/${google_cloud_run_v2_service.api.name}"
    error_message = "Audience binds existing project and actual service"
  }
}
run "deny_project_number_mismatch" {
  command         = plan
  expect_failures = [check.existing_project_number, google_cloud_run_v2_service.api]
  override_data {
    target = data.google_project.existing
    values = { number = "111111111111" }
  }
}
run "deny_activation_without_origin" {
  command = plan
  variables {
    enable_application = true
  }
  expect_failures = [google_cloud_run_v2_service.api]
}
run "deny_mutable_application_image" {
  command = plan
  variables {
    application_image = "offline.invalid/review/app:latest"
  }
  expect_failures = [var.application_image]
}
run "deny_mutable_proxy_image" {
  command = plan
  variables {
    sql_proxy_image = "offline.invalid/review/proxy:latest"
  }
  expect_failures = [var.sql_proxy_image]
}
run "deny_latest_token_version" {
  command = plan
  variables {
    destination_token_version = "latest"
  }
  expect_failures = [var.destination_token_version]
}
run "deny_non_https_destination" {
  command = plan
  variables {
    destination_url = "http://independent.example.test/route"
  }
  expect_failures = [var.destination_url]
}
run "deny_image_family" {
  command = plan
  variables {
    worker_os_image = "projects/cos-cloud/global/images/family/cos-stable"
  }
  expect_failures = [var.worker_os_image]
}
