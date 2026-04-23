# ─────────────────────────────────────────────
# EVENT HUB NAMESPACE + HUB
# Think of this as a high-speed conveyor belt.
# Messages coming out of IoT Hub get passed here
# so Stream Analytics can read them in real time.
# ─────────────────────────────────────────────
resource "azurerm_eventhub_namespace" "main" {
  name                = "evhns-${local.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  capacity            = 1
  tags                = local.tags
}

resource "azurerm_eventhub" "alerts" {
  name                = "evh-alerts"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = 2
  message_retention   = 1
}

# Consumer group — Stream Analytics uses this to
# read messages without conflicting with other readers
resource "azurerm_eventhub_consumer_group" "stream_analytics" {
  name                = "cg-stream-analytics"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.alerts.name
  resource_group_name = azurerm_resource_group.main.name
}

# Access key so Stream Analytics can authenticate
# and read from the Event Hub
resource "azurerm_eventhub_authorization_rule" "listen" {
  name                = "rule-listen"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.alerts.name
  resource_group_name = azurerm_resource_group.main.name
  listen              = true
  send                = false
  manage              = false
}

resource "azurerm_eventhub_authorization_rule" "send" {
  name                = "rule-send"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.alerts.name
  resource_group_name = azurerm_resource_group.main.name
  listen              = false
  send                = true
  manage              = false
}

# ─────────────────────────────────────────────
# IOT HUB
# This is the post office. Every simulated device
# — warehouse sensors, hospital servers — sends
# its messages here. IoT Hub receives them all
# and forwards them to the Event Hub conveyor belt.
# ─────────────────────────────────────────────
resource "azurerm_iothub" "main" {
  name                = "ioth-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags

  sku {
    name     = "F1"   # Free tier — 8,000 messages per day, no cost
    capacity = 1
  }

  # Route messages to Event Hub so Stream Analytics can process them
  endpoint {
    type                       = "AzureIotHub.EventHub"
    connection_string          = azurerm_eventhub_authorization_rule.send.primary_connection_string
    name                       = "export-to-eventhub"
    resource_group_name        = azurerm_resource_group.main.name
    batch_frequency_in_seconds = 60
    max_chunk_size_in_bytes    = 10485760
    encoding                   = "JSON"
  }

  route {
    name           = "route-all-to-eventhub"
    source         = "DeviceMessages"
    condition      = "true"
    endpoint_names = ["export-to-eventhub"]
    enabled        = true
  }

  # Also send to the built-in endpoint (used by the simulator script)
  fallback_route {
    source         = "DeviceMessages"
    condition      = "true"
    endpoint_names = ["events"]
    enabled        = true
  }

  lifecycle {
    ignore_changes = [
      min_tls_version,
      endpoint,
      enrichment,
      cloud_to_device,
      shared_access_policy,
    ]
  }
}

# Note: Device registration (warehouse-sensor-01, clinical-server-01)
# is done via the Azure CLI after deployment — see ARCHITECTURE.md
# The simulator script handles its own device connection string.

# Store IoT Hub connection string in Key Vault
# so the simulator script can retrieve it securely
resource "azurerm_key_vault_secret" "iothub_connection" {
  name         = "iothub-connection-string"
  value        = "HostName=${azurerm_iothub.main.hostname};SharedAccessKeyName=iothubowner;SharedAccessKey=${azurerm_iothub.main.shared_access_policy[0].primary_key}"
  key_vault_id = azurerm_key_vault.main.id
  tags         = local.tags
}
