# Project 14: Inventory Watchdog
# Least-privilege access for the scan engine. The Function reads and
# writes the lake and calls GPT-4o using its identity alone. Zero keys
# in code or app settings.

resource "azurerm_role_assignment" "func_lake_access" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.watchdog.identity[0].principal_id
}

resource "azurerm_role_assignment" "func_openai_access" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_linux_function_app.watchdog.identity[0].principal_id
}
