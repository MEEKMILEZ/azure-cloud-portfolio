resource "azurerm_service_plan" "main" {
  name                = "asp-promptguard-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = "B1"

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_storage_account" "function_storage" {
  name                     = "stfnpg${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_linux_function_app" "classify" {
  name                       = "fn-promptguard-${random_string.suffix.result}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  service_plan_id            = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.function_storage.name
  storage_account_access_key = azurerm_storage_account.function_storage.primary_access_key

  site_config {
    application_stack {
      python_version = "3.11"
    }
    cors {
      allowed_origins     = ["*"]
      support_credentials = false
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME       = "python"
    AzureWebJobsFeatureFlags       = "EnableWorkerIndexing"
    KEY_VAULT_URL                  = azurerm_key_vault.main.vault_uri
    OPENAI_ENDPOINT                = azurerm_cognitive_account.openai.endpoint
    OPENAI_API_KEY                 = azurerm_cognitive_account.openai.primary_access_key
    OPENAI_DEPLOYMENT              = azurerm_cognitive_deployment.gpt4o.name
    STORAGE_CONNECTION_STRING      = azurerm_storage_account.main.primary_connection_string
    AUDIT_CONTAINER                = azurerm_storage_container.audit_logs.name
  }

  identity {
    type = "SystemAssigned"
  }

  tags = azurerm_resource_group.main.tags
}

# Give Function App access to Key Vault
resource "azurerm_key_vault_access_policy" "function_app" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_function_app.classify.identity[0].principal_id

  secret_permissions = ["Get", "List"]
}
