# Project 14: Inventory Watchdog
# Digest delivery shell. The workflow resource is created now so the
# skeleton is complete in Terraform. The outlook connector and the
# email steps get wired in Phase 4, with connector authentication done
# once in the portal per standing convention.
#
# Lesson carried from Project 11: use the outlook managed API for
# personal Outlook and Hotmail accounts, not the Office 365 connector.

resource "azurerm_logic_app_workflow" "digest" {
  name                = "logic-invwatch-digest-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}
