resource "azurerm_automation_account" "main" {
  name                = "auto-helpdesk-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku_name            = "Basic"

  identity {
    type = "SystemAssigned"
  }

  tags = azurerm_resource_group.main.tags
}
