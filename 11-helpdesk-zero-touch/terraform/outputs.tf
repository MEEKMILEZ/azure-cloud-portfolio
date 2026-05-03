output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "unique_suffix" {
  value = random_string.suffix.result
}

output "function_app_name" {
  value = azurerm_linux_function_app.main.name
}

output "function_app_url" {
  value = "https://${azurerm_linux_function_app.main.default_hostname}/api"
}

output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "automation_account_name" {
  value = azurerm_automation_account.main.name
}

output "logic_app_name" {
  value = azurerm_logic_app_workflow.notifications.name
}
