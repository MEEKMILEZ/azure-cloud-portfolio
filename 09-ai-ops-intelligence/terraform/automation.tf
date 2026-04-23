# ─────────────────────────────────────────────
# AUTOMATION ACCOUNT
# Think of this as a robot that can run scripts
# on a schedule inside Azure. It runs our DR
# validation test every week without anyone
# having to trigger it manually.
# ─────────────────────────────────────────────
resource "azurerm_automation_account" "main" {
  name                = "aa-${local.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku_name            = "Basic"
  tags                = local.tags

  # System-assigned identity lets the runbook
  # talk to other Azure services securely
  identity {
    type = "SystemAssigned"
  }
}

# Give the Automation Account permission to
# read from Key Vault so the runbook can
# retrieve secrets at runtime
resource "azurerm_key_vault_access_policy" "automation" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_automation_account.main.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List"
  ]
}

# ─────────────────────────────────────────────
# DR VALIDATION RUNBOOK
# This is the PowerShell script that runs the
# weekly DR test. It:
# 1. Checks all backup jobs completed successfully
# 2. Measures how long a simulated recovery takes
# 3. Compares against your RTO/RPO targets
# 4. Calls Azure OpenAI to write a plain English report
# 5. Saves the report to Blob Storage
# ─────────────────────────────────────────────
resource "azurerm_automation_runbook" "dr_validation" {
  name                    = "runbook-dr-validation"
  location                = azurerm_resource_group.main.location
  resource_group_name     = azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.main.name
  log_verbose             = true
  log_progress            = true
  runbook_type            = "PowerShell"
  tags                    = local.tags

  description = "Weekly DR validation — simulates failover, measures RTO/RPO, generates AI health report"

  publish_content_link {
    uri = "https://raw.githubusercontent.com/MEEKMILEZ/azure-cloud-portfolio/main/09-ai-ops-intelligence/scripts/dr-runbook.ps1"
  }
}

# Schedule the runbook to run every Monday at 6am UTC
# (Logic Apps also triggers this — this is the backup schedule)
resource "azurerm_automation_schedule" "weekly_monday" {
  name                    = "schedule-weekly-monday"
  resource_group_name     = azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.main.name
  frequency               = "Week"
  interval                = 1
  timezone                = "UTC"
  start_time              = "2026-05-05T06:00:00Z"
  description             = "Runs every Monday at 6am UTC"

  week_days = ["Monday"]
}

# Link the schedule to the runbook
resource "azurerm_automation_job_schedule" "dr_weekly" {
  resource_group_name     = azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.main.name
  schedule_name           = azurerm_automation_schedule.weekly_monday.name
  runbook_name            = azurerm_automation_runbook.dr_validation.name
}

# Store the Automation Account name in Key Vault
# so Logic Apps can trigger the runbook by name
resource "azurerm_key_vault_secret" "automation_account_name" {
  name         = "automation-account-name"
  value        = azurerm_automation_account.main.name
  key_vault_id = azurerm_key_vault.main.id
  tags         = local.tags
}
