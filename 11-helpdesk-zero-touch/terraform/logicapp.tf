resource "azurerm_logic_app_workflow" "notifications" {
  name                = "logic-helpdesk-notify-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_logic_app_trigger_http_request" "notify_trigger" {
  name         = "notification-received"
  logic_app_id = azurerm_logic_app_workflow.notifications.id

  schema = <<SCHEMA
{
  "type": "object",
  "properties": {
    "event_type":  { "type": "string" },
    "user":        { "type": "string" },
    "action":      { "type": "string" },
    "details":     { "type": "string" },
    "timestamp":   { "type": "string" }
  }
}
SCHEMA
}
