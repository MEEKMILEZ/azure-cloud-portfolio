# These values are printed to your terminal after
# "terraform apply" finishes. You'll need them to
# configure the later phases (IoT Hub, OpenAI, etc.)

output "resource_group_name" {
  description = "Name of the Azure resource group containing all project resources"
  value       = azurerm_resource_group.main.name
}

output "log_analytics_workspace_id" {
  description = "ID of the central log workspace — needed when connecting other services"
  value       = azurerm_log_analytics_workspace.main.id
}

output "storage_account_name" {
  description = "Name of the storage account that holds AI reports and alert logs"
  value       = azurerm_storage_account.main.name
}

output "key_vault_name" {
  description = "Name of the Key Vault — open this in the Azure portal to verify secrets were stored"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "Web address of the Key Vault — used by scripts to retrieve secrets"
  value       = azurerm_key_vault.main.vault_uri
}

output "unique_suffix" {
  description = "The random suffix appended to all resource names — useful for finding them in the portal"
  value       = random_string.suffix.result
}
