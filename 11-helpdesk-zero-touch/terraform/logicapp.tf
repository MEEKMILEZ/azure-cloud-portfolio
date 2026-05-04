# ============================================================
# OFFICE 365 OUTLOOK MANAGED API + CONNECTION
# Terraform creates the connection. The OAuth sign in must be
# completed once in the Azure Portal (one click) after apply.
# This is a Microsoft platform limitation, not a Terraform one.
# ============================================================

data "azurerm_managed_api" "office365" {
  name     = "office365"
  location = azurerm_resource_group.main.location
}

resource "azurerm_api_connection" "office365" {
  name                = "office365-helpdesk"
  resource_group_name = azurerm_resource_group.main.name
  managed_api_id      = data.azurerm_managed_api.office365.id
  display_name        = "Lakeshore Regional IT Notifications"

  # parameter_values cannot be set via Terraform for OAuth connectors.
  # Authorization happens once via the Portal after first apply.
  lifecycle {
    ignore_changes = [parameter_values]
  }

  tags = azurerm_resource_group.main.tags
}

# ============================================================
# LOGIC APP WORKFLOW
# Defined entirely via the workflow_parameters / workflow_schema
# pair plus a hand built definition. The trigger and action are
# defined inline rather than via separate Terraform resources so
# the Office 365 send_email action body can be expressed properly.
# ============================================================

resource "azurerm_logic_app_workflow" "notifications" {
  name                = "logic-helpdesk-notify-${local.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  parameters = {
    "$connections" = jsonencode({
      office365 = {
        connectionId   = azurerm_api_connection.office365.id
        connectionName = "office365-helpdesk"
        id             = data.azurerm_managed_api.office365.id
      }
    })
  }

  workflow_parameters = {
    "$connections" = jsonencode({
      defaultValue = {}
      type         = "Object"
    })
  }

  tags = azurerm_resource_group.main.tags

  depends_on = [azurerm_api_connection.office365]
}

# ============================================================
# HTTP REQUEST TRIGGER
# Receives JSON from the Function App with the email payload.
# ============================================================

resource "azurerm_logic_app_trigger_http_request" "notify_trigger" {
  name         = "notification-received"
  logic_app_id = azurerm_logic_app_workflow.notifications.id

  schema = <<SCHEMA
{
  "type": "object",
  "properties": {
    "to":                { "type": "string" },
    "subject":           { "type": "string" },
    "body_html":         { "type": "string" },
    "notification_type": { "type": "string" },
    "audit_ref":         { "type": "string" },
    "importance":        { "type": "string" }
  },
  "required": ["to", "subject", "body_html"]
}
SCHEMA
}

# ============================================================
# SEND EMAIL ACTION
# azurerm_logic_app_action_custom lets us inject the raw JSON
# body for the Office 365 Send_an_email_V2 action, which the
# higher level resources do not support.
# ============================================================

resource "azurerm_logic_app_action_custom" "send_email" {
  name         = "Send_an_email_V2"
  logic_app_id = azurerm_logic_app_workflow.notifications.id

  body = jsonencode({
    type = "ApiConnection"
    inputs = {
      host = {
        connection = {
          name = "@parameters('$connections')['office365']['connectionId']"
        }
      }
      method = "post"
      path   = "/v2/Mail"
      body = {
        To         = "@triggerBody()?['to']"
        Subject    = "@triggerBody()?['subject']"
        Body       = "@triggerBody()?['body_html']"
        Importance = "@coalesce(triggerBody()?['importance'], 'Normal')"
      }
    }
    runAfter = {}
  })

  depends_on = [azurerm_logic_app_trigger_http_request.notify_trigger]
}

# ============================================================
# RESPONSE ACTION
# Returns the message_id and audit_ref to the Function App.
# ============================================================

resource "azurerm_logic_app_action_custom" "send_response" {
  name         = "Response"
  logic_app_id = azurerm_logic_app_workflow.notifications.id

  body = jsonencode({
    type = "Response"
    inputs = {
      statusCode = 200
      headers    = { "Content-Type" = "application/json" }
      body = {
        sent       = true
        run_id     = "@workflow().run.name"
        sent_at    = "@utcNow()"
        recipient  = "@triggerBody()?['to']"
        audit_ref  = "@triggerBody()?['audit_ref']"
      }
    }
    runAfter = {
      "Send_an_email_V2" = ["Succeeded"]
    }
  })

  depends_on = [azurerm_logic_app_action_custom.send_email]
}

# ============================================================
# The trigger callback URL (with SAS signature) is exposed
# directly on azurerm_logic_app_trigger_http_request as the
# callback_url attribute. functionapp.tf reads it from there.
# ============================================================
