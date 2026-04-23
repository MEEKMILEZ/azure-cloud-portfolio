# ─────────────────────────────────────────────
# LOG ANALYTICS WORKSPACE
# Think of this as the central logbook for the
# entire project. Every service writes its logs
# here so you can search and query everything
# from one place.
# ─────────────────────────────────────────────
resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${local.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

# ─────────────────────────────────────────────
# STORAGE ACCOUNT
# This is like a filing cabinet in the cloud.
# It holds the AI-generated DR reports and
# alert triage summaries as text files.
# ─────────────────────────────────────────────
resource "azurerm_storage_account" "main" {
  name                     = "st${replace(local.prefix, "-", "")}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"  # Locally redundant — fine for dev
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

# A container is like a folder inside the storage account
resource "azurerm_storage_container" "reports" {
  name                  = "ai-reports"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "alerts" {
  name                  = "alert-triage"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# ─────────────────────────────────────────────
# KEY VAULT
# This is a secure safe for secrets — API keys,
# passwords, connection strings. Nothing sensitive
# is ever stored in plain text in your code.
# ─────────────────────────────────────────────
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                        = "kv-${local.prefix}"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  purge_protection_enabled    = false
  soft_delete_retention_days  = 7
  tags                        = local.tags

  # This gives YOUR Azure account permission to manage secrets in the vault
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get", "List", "Set", "Delete", "Recover", "Backup", "Restore", "Purge"
    ]
  }
}

# Store the storage account connection string as a secret
# (so scripts can retrieve it securely at runtime)
resource "azurerm_key_vault_secret" "storage_connection" {
  name         = "storage-connection-string"
  value        = azurerm_storage_account.main.primary_connection_string
  key_vault_id = azurerm_key_vault.main.id
  tags         = local.tags
}
