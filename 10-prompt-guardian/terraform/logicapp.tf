resource "azurerm_logic_app_workflow" "override_notify" {
  name                = "logic-override-notify-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_logic_app_trigger_http_request" "override_trigger" {
  name         = "override-received"
  logic_app_id = azurerm_logic_app_workflow.override_notify.id

  schema = <<SCHEMA
{
  "type": "object",
  "properties": {
    "timestamp":              { "type": "string" },
    "user_id":                { "type": "string" },
    "original_action":        { "type": "string" },
    "original_category":      { "type": "string" },
    "original_severity":      { "type": "string" },
    "override_reason":        { "type": "string" },
    "override_justification": { "type": "string" },
    "prompt_length":          { "type": "integer" },
    "prompt_preview":         { "type": "string" },
    "audit_ref":              { "type": "string" }
  }
}
SCHEMA
}
