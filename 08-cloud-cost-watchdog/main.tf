terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id            = "d63dea0b-8971-4058-b105-e9608a3b1db8"
  skip_provider_registration = true
}

data "azurerm_resource_group" "main" {
  name = "RG-CostWatchdog"
}

data "azurerm_subscription" "current" {}

resource "azurerm_automation_account" "watchdog" {
  name                = "aa-cost-watchdog"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku_name            = "Basic"

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_role_assignment" "reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Reader"
  principal_id         = azurerm_automation_account.watchdog.identity[0].principal_id
}

resource "azurerm_automation_module" "az_accounts" {
  name                    = "Az.Accounts"
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.watchdog.name

  module_link {
    uri = "https://www.powershellgallery.com/api/v2/package/Az.Accounts/3.0.5"
  }
}

resource "azurerm_automation_module" "az_compute" {
  name                    = "Az.Compute"
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.watchdog.name

  module_link {
    uri = "https://www.powershellgallery.com/api/v2/package/Az.Compute/8.3.0"
  }

  depends_on = [azurerm_automation_module.az_accounts]
}

resource "azurerm_automation_module" "az_network" {
  name                    = "Az.Network"
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.watchdog.name

  module_link {
    uri = "https://www.powershellgallery.com/api/v2/package/Az.Network/7.12.0"
  }

  depends_on = [azurerm_automation_module.az_accounts]
}

resource "azurerm_automation_module" "az_resources" {
  name                    = "Az.Resources"
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.watchdog.name

  module_link {
    uri = "https://www.powershellgallery.com/api/v2/package/Az.Resources/7.5.0"
  }

  depends_on = [azurerm_automation_module.az_accounts]
}

resource "azurerm_automation_schedule" "daily_scan" {
  name                    = "Daily-Zombie-Scan"
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.watchdog.name
  frequency               = "Day"
  interval                = 1
  start_time              = "2026-04-08T06:00:00Z"
  description             = "Runs zombie resource scan daily at 6:00 AM UTC"
}

resource "azurerm_automation_job_schedule" "scan_schedule" {
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.watchdog.name
  runbook_name            = "Scan-ZombieResources"
  schedule_name           = azurerm_automation_schedule.daily_scan.name
}

resource "azurerm_monitor_action_group" "cost_report" {
  name                = "ag-cost-report"
  resource_group_name = data.azurerm_resource_group.main.name
  short_name          = "costreport"

  email_receiver {
    name          = "AdminEmail"
    email_address = "paschalnnennal@hotmail.com"
  }
}

resource "azurerm_logic_app_workflow" "cost_report" {
  name                = "la-cost-report"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
}

output "automation_account_id" {
  value = azurerm_automation_account.watchdog.id
}

output "managed_identity_principal_id" {
  value = azurerm_automation_account.watchdog.identity[0].principal_id
}

output "logic_app_id" {
  value = azurerm_logic_app_workflow.cost_report.id
}

output "action_group_id" {
  value = azurerm_monitor_action_group.cost_report.id
}
