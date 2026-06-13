# Project 14: Inventory Watchdog
# Resource group and naming suffix

resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}

locals {
  suffix = random_string.suffix.result
  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-invwatch-${var.environment}-${local.suffix}"
  location = var.location
  tags     = local.tags
}
