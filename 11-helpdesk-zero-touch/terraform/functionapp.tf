resource "azurerm_service_plan" "main" {
  name                = "asp-helpdesk-${local.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = "B1"

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_linux_function_app" "main" {
  name                       = "fn-helpdesk-${local.suffix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  service_plan_id            = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.function_storage.name
  storage_account_access_key = azurerm_storage_account.function_storage.primary_access_key

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"  = "python"
    "AzureWebJobsFeatureFlags"  = "EnableWorkerIndexing"
    "OPENAI_ENDPOINT"           = azurerm_cognitive_account.openai.endpoint
    "OPENAI_API_KEY"            = azurerm_cognitive_account.openai.primary_access_key
    "OPENAI_DEPLOYMENT"         = "gpt-4o"
    "STORAGE_CONNECTION_STRING" = azurerm_storage_account.main.primary_connection_string
    "KEY_VAULT_URL"             = azurerm_key_vault.main.vault_uri
    "IDENTITY_LOG_CONTAINER"    = "identity-logs"
    "TRIAGE_LOG_CONTAINER"      = "triage-logs"
    "DRIFT_REPORT_CONTAINER"    = "drift-reports"
    "KB_CONTAINER"              = "kb-articles"

    # Email integration via Logic App
    "LOGIC_APP_NOTIFY_URL"      = azurerm_logic_app_trigger_http_request.notify_trigger.callback_url
    "NOTIFY_FROM_NAME"          = "Lakeshore Regional IT"
    "MANAGER_EMAIL_OVERRIDE"    = "Paschalnnenna@hotmail.com"
  }

  site_config {
    ftps_state = "Disabled"

    application_stack {
      python_version = "3.11"
    }

    cors {
      allowed_origins = ["*"]
    }
  }

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_key_vault_access_policy" "function_app" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_function_app.main.identity[0].principal_id

  secret_permissions = ["Get", "List"]
}
