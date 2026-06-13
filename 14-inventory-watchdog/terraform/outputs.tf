# Project 14: Inventory Watchdog
# Outputs used by later phases

output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "lake_account_name" {
  value = azurerm_storage_account.lake.name
}

output "lake_dfs_endpoint" {
  value = azurerm_storage_account.lake.primary_dfs_endpoint
}

output "function_app_name" {
  value = azurerm_linux_function_app.watchdog.name
}

output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "logic_app_name" {
  value = azurerm_logic_app_workflow.digest.name
}
