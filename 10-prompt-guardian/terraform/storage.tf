resource "azurerm_storage_account" "main" {
  name                     = "stpromptguard${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = azurerm_resource_group.main.tags
}

# Audit log container — append-only, immutable
resource "azurerm_storage_container" "audit_logs" {
  name                  = "audit-logs"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Immutable storage policy — prevents deletion or modification of blobs
resource "azurerm_storage_management_policy" "audit_retention" {
  storage_account_id = azurerm_storage_account.main.id

  rule {
    name    = "retain-audit-logs"
    enabled = true

    filters {
      blob_types   = ["appendBlob", "blockBlob"]
      prefix_match = ["audit-logs/"]
    }

    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 2555
      }
    }
  }
}
