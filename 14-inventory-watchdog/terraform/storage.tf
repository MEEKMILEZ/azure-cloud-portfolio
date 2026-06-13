# Project 14: Inventory Watchdog
# Data lake storage with medallion architecture
#
# Two storage accounts on purpose:
# 1. The lake account holds business data. Hierarchical namespace on,
#    which is the one flag that turns Blob Storage into ADLS Gen2.
# 2. A small plain account for the Function App runtime internals,
#    keeping app plumbing separate from business data.

resource "azurerm_storage_account" "lake" {
  name                     = "stinvwatchlake${local.suffix}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

# Medallion zones. Bronze holds raw extracts, silver holds cleaned
# Parquet, gold holds watchdog findings ready for reporting.

resource "azurerm_storage_data_lake_gen2_filesystem" "bronze" {
  name               = "bronze"
  storage_account_id = azurerm_storage_account.lake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "silver" {
  name               = "silver"
  storage_account_id = azurerm_storage_account.lake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "gold" {
  name               = "gold"
  storage_account_id = azurerm_storage_account.lake.id
}

# Runtime storage for the Function App. No hierarchical namespace needed.

resource "azurerm_storage_account" "func" {
  name                     = "stinvwatchfn${local.suffix}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}
