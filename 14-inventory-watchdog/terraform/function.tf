# Project 14: Inventory Watchdog
# Scan engine host. Python Function App on the Consumption plan,
# meaning we pay only when the timer fires. System-assigned managed
# identity so the code never touches a storage key or an OpenAI key.

resource "azurerm_service_plan" "func" {
  name                = "asp-invwatch-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "Y1"
  tags                = local.tags
}

resource "azurerm_linux_function_app" "watchdog" {
  name                       = "func-invwatch-${local.suffix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  service_plan_id            = azurerm_service_plan.func.id
  storage_account_name       = azurerm_storage_account.func.name
  storage_account_access_key = azurerm_storage_account.func.primary_access_key

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    LAKE_ACCOUNT_NAME      = azurerm_storage_account.lake.name
    LAKE_DFS_ENDPOINT      = azurerm_storage_account.lake.primary_dfs_endpoint
    OPENAI_ENDPOINT        = azurerm_cognitive_account.openai.endpoint
    OPENAI_DEPLOYMENT_NAME = azurerm_cognitive_deployment.narrator.name
  }

  tags = local.tags
}
