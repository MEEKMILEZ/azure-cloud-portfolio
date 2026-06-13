# Project 14: Inventory Watchdog
# Digest delivery. Recurrence every Monday 11:30 UTC, thirty minutes
# after the scan timer, fetch the digest from the Function over HTTP,
# email it through the outlook connector.
#
# Lesson carried from Project 11: use the outlook managed API for
# personal Outlook and Hotmail accounts, not the Office 365 connector.
# The connection is authorized once in the portal after apply, which
# is the one permitted portal step per house convention.

data "azurerm_managed_api" "outlook" {
  name     = "outlook"
  location = azurerm_resource_group.main.location
}

resource "azurerm_api_connection" "outlook" {
  name                = "outlook"
  resource_group_name = azurerm_resource_group.main.name
  managed_api_id      = data.azurerm_managed_api.outlook.id
  display_name        = "Inventory Watchdog mailer"

  lifecycle {
    # Authorization happens in the portal and writes values Terraform
    # does not manage. Ignore them so later applies do not undo it.
    ignore_changes = [parameter_values]
  }
}

data "azurerm_function_app_host_keys" "watchdog" {
  name                = azurerm_linux_function_app.watchdog.name
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_logic_app_workflow" "digest" {
  name                = "logic-invwatch-digest-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  workflow_parameters = {
    "$connections" = jsonencode({
      type         = "Object"
      defaultValue = {}
    })
  }

  parameters = {
    "$connections" = jsonencode({
      outlook = {
        connectionId   = azurerm_api_connection.outlook.id
        connectionName = azurerm_api_connection.outlook.name
        id             = data.azurerm_managed_api.outlook.id
      }
    })
  }

  tags = local.tags
}

resource "azurerm_logic_app_trigger_recurrence" "monday" {
  name         = "every-monday"
  logic_app_id = azurerm_logic_app_workflow.digest.id
  frequency    = "Week"
  interval     = 1
  time_zone    = "UTC"

  schedule {
    on_these_days = ["Monday"]
    at_these_hours   = [11]
    at_these_minutes = [30]
  }
}

resource "azurerm_logic_app_action_custom" "get_digest" {
  name         = "get-digest"
  logic_app_id = azurerm_logic_app_workflow.digest.id

  body = jsonencode({
    type = "Http"
    inputs = {
      method = "GET"
      uri    = "https://${azurerm_linux_function_app.watchdog.default_hostname}/api/get-digest"
      queries = {
        code = data.azurerm_function_app_host_keys.watchdog.default_function_key
      }
    }
    runAfter = {}
  })
}

resource "azurerm_logic_app_action_custom" "send_email" {
  name         = "send-digest-email"
  logic_app_id = azurerm_logic_app_workflow.digest.id

  # The runAfter reference lives inside opaque JSON, so Terraform
  # cannot infer the ordering. Declare it or parallel creation races.
  depends_on = [azurerm_logic_app_action_custom.get_digest]

  body = jsonencode({
    type = "ApiConnection"
    inputs = {
      host = {
        connection = {
          name = "@parameters('$connections')['outlook']['connectionId']"
        }
      }
      method = "post"
      path   = "/v2/Mail"
      body = {
        To         = var.digest_recipient
        Subject    = "Inventory Watchdog weekly digest, Northbridge Medical Supply"
        Body       = "<pre style=\"font-family:Consolas,monospace\">@{body('get-digest')}</pre>"
        Importance = "Normal"
      }
    }
    runAfter = {
      "get-digest" = ["Succeeded"]
    }
  })
}
