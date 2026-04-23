# ─────────────────────────────────────────────
# LOGIC APPS — THE DELIVERY PERSON
# Logic Apps watches for flagged anomalies,
# calls the AI triage function, and routes
# results to email. It also triggers the weekly
# DR validation on a schedule.
#
# NOTE: Per project convention, Logic App
# connector authentication (email, Teams) is
# done via the portal only — not in Terraform.
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# ALERT TRIAGE WORKFLOW
# Triggered when a new anomaly lands in the
# Event Hub. Calls the triage function and
# sends an email with the AI verdict.
# ─────────────────────────────────────────────
resource "azurerm_logic_app_workflow" "alert_triage" {
  name                = "logic-alert-triage-${local.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags

  workflow_parameters = {
    "$connections" = jsonencode({
      defaultValue = {}
      type         = "Object"
    })
  }
}

# ─────────────────────────────────────────────
# DR VALIDATION WORKFLOW
# Runs on a weekly schedule — every Monday
# at 6am. Triggers the Automation Runbook
# that simulates a DR failover and generates
# the AI health report.
# ─────────────────────────────────────────────
resource "azurerm_logic_app_workflow" "dr_validation" {
  name                = "logic-dr-validation-${local.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

# Weekly schedule trigger — every Monday at 6am UTC
resource "azurerm_logic_app_trigger_recurrence" "weekly_dr" {
  name         = "trigger-weekly-monday"
  logic_app_id = azurerm_logic_app_workflow.dr_validation.id
  frequency    = "Week"
  interval     = 1

  schedule {
    at_these_hours   = [6]
    at_these_minutes = [0]
    on_these_days    = ["Monday"]
  }
}

# ─────────────────────────────────────────────
# ACTION GROUP
# This is the contact list Azure Monitor uses
# to know WHO to notify when an alert fires.
# Logic Apps also uses this as a fallback
# direct notification channel.
# ─────────────────────────────────────────────
resource "azurerm_monitor_action_group" "main" {
  name                = "ag-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "aiops-ag"
  tags                = local.tags

  email_receiver {
    name                    = "ops-team-email"
    email_address           = var.notification_email
    use_common_alert_schema = true
  }
}

# ─────────────────────────────────────────────
# AZURE MONITOR ALERT RULES
# These watch for high-level infrastructure
# issues and feed into the action group above.
# Stream Analytics handles the IoT-level
# anomaly detection — these cover the Azure
# infrastructure layer itself.
# ─────────────────────────────────────────────

# Alert if Stream Analytics job stops running
resource "azurerm_monitor_metric_alert" "stream_analytics_errors" {
  name                = "alert-asa-errors-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_stream_analytics_job.main.id]
  description         = "Fires if Stream Analytics stops processing events or encounters errors"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  tags                = local.tags

  criteria {
    metric_namespace = "Microsoft.StreamAnalytics/streamingjobs"
    metric_name      = "Errors"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
}

# Alert if IoT Hub starts dropping messages
resource "azurerm_monitor_metric_alert" "iothub_dropped_messages" {
  name                = "alert-iothub-drops-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_iothub.main.id]
  description         = "Fires if IoT Hub starts dropping device messages"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  tags                = local.tags

  criteria {
    metric_namespace = "Microsoft.Devices/IotHubs"
    metric_name      = "d2c.telemetry.egress.dropped"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
}

# Store Logic App endpoints in Key Vault for
# the triage function to call back into
resource "azurerm_key_vault_secret" "alert_triage_callback_url" {
  name         = "logic-alert-triage-id"
  value        = azurerm_logic_app_workflow.alert_triage.id
  key_vault_id = azurerm_key_vault.main.id
  tags         = local.tags
}
