# ─────────────────────────────────────────────
# STREAM ANALYTICS JOB
# This is the smart filter. It sits on the Event
# Hub conveyor belt, reads every message as it
# arrives, and flags the ones that look suspicious.
# It runs a continuous SQL-like query 24/7.
# ─────────────────────────────────────────────
resource "azurerm_stream_analytics_job" "main" {
  name                                     = "asa-${local.prefix}"
  resource_group_name                      = azurerm_resource_group.main.name
  location                                 = azurerm_resource_group.main.location
  compatibility_level                      = "1.2"
  data_locale                              = "en-US"
  events_late_arrival_max_delay_in_seconds = 60
  events_out_of_order_max_delay_in_seconds = 50
  events_out_of_order_policy               = "Adjust"
  output_error_policy                      = "Drop"
  streaming_units                          = 1
  tags                                     = local.tags

  # This is the detection query — plain English explanation:
  # Every 5 minutes, look at all incoming messages.
  # Flag any device where:
  #   - Temperature spiked above normal (>85°C for warehouse, >75°C for servers)
  #   - OR vibration is unusually high (>0.8 for warehouse equipment)
  #   - OR packet loss is too high (>5% for clinical network gear)
  # Output those flagged messages to the alerts Event Hub.
  transformation_query = <<-QUERY
    -- Warehouse equipment anomaly detection
    SELECT
        deviceId,
        'warehouse' AS industry,
        AVG(temperature) AS avg_temperature,
        AVG(vibration) AS avg_vibration,
        MAX(temperature) AS max_temperature,
        COUNT(*) AS message_count,
        System.Timestamp() AS window_end_time,
        CASE
            WHEN AVG(temperature) > 85 AND AVG(vibration) > 0.8
                THEN 'CRITICAL'
            WHEN AVG(temperature) > 75 OR AVG(vibration) > 0.6
                THEN 'WARNING'
            ELSE 'NORMAL'
        END AS severity
    INTO [output-alerts]
    FROM [input-iothub] TIMESTAMP BY EventEnqueuedUtcTime
    WHERE industry = 'warehouse'
    GROUP BY deviceId, industry, TumblingWindow(minute, 5)
    HAVING
        AVG(temperature) > 75 OR AVG(vibration) > 0.6

    UNION ALL

    -- Clinical / healthcare server anomaly detection
    SELECT
        deviceId,
        'healthcare' AS industry,
        AVG(temperature) AS avg_temperature,
        AVG(packet_loss_pct) AS avg_packet_loss,
        AVG(cpu_pct) AS avg_cpu,
        COUNT(*) AS message_count,
        System.Timestamp() AS window_end_time,
        CASE
            WHEN AVG(cpu_pct) > 90 AND AVG(packet_loss_pct) > 3
                THEN 'CRITICAL'
            WHEN AVG(cpu_pct) > 80 OR AVG(packet_loss_pct) > 2
                THEN 'WARNING'
            ELSE 'NORMAL'
        END AS severity
    INTO [output-alerts]
    FROM [input-iothub] TIMESTAMP BY EventEnqueuedUtcTime
    WHERE industry = 'healthcare'
    GROUP BY deviceId, industry, TumblingWindow(minute, 5)
    HAVING
        AVG(cpu_pct) > 80 OR AVG(packet_loss_pct) > 2
  QUERY
}

# ─────────────────────────────────────────────
# STREAM ANALYTICS INPUT
# This tells Stream Analytics where to read
# messages FROM — our IoT Hub Event Hub endpoint
# ─────────────────────────────────────────────
resource "azurerm_stream_analytics_stream_input_eventhub" "iothub_input" {
  name                         = "input-iothub"
  stream_analytics_job_name    = azurerm_stream_analytics_job.main.name
  resource_group_name          = azurerm_resource_group.main.name
  eventhub_consumer_group_name = azurerm_eventhub_consumer_group.stream_analytics.name
  eventhub_name                = azurerm_eventhub.alerts.name
  servicebus_namespace         = azurerm_eventhub_namespace.main.name
  shared_access_policy_key     = azurerm_eventhub_authorization_rule.listen.primary_key
  shared_access_policy_name    = azurerm_eventhub_authorization_rule.listen.name

  serialization {
    type     = "Json"
    encoding = "UTF8"
  }
}

# ─────────────────────────────────────────────
# STREAM ANALYTICS OUTPUT
# This tells Stream Analytics where to SEND
# flagged anomalies — back to a separate Event Hub
# that Logic Apps will watch and act on
# ─────────────────────────────────────────────

# Second Event Hub specifically for anomaly output
resource "azurerm_eventhub" "anomalies" {
  name                = "evh-anomalies"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = 2
  message_retention   = 1
}

resource "azurerm_eventhub_authorization_rule" "anomalies_send" {
  name                = "rule-anomalies-send"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.anomalies.name
  resource_group_name = azurerm_resource_group.main.name
  listen              = true
  send                = true
  manage              = false
}

resource "azurerm_stream_analytics_output_eventhub" "anomaly_output" {
  name                      = "output-alerts"
  stream_analytics_job_name = azurerm_stream_analytics_job.main.name
  resource_group_name       = azurerm_resource_group.main.name
  eventhub_name             = azurerm_eventhub.anomalies.name
  servicebus_namespace      = azurerm_eventhub_namespace.main.name
  shared_access_policy_key  = azurerm_eventhub_authorization_rule.anomalies_send.primary_key
  shared_access_policy_name = azurerm_eventhub_authorization_rule.anomalies_send.name

  serialization {
    type     = "Json"
    encoding = "UTF8"
    format   = "LineSeparated"
  }
}

# Store anomaly Event Hub connection string in Key Vault
# Logic Apps will retrieve this to watch for flagged alerts
resource "azurerm_key_vault_secret" "anomaly_eventhub_connection" {
  name         = "anomaly-eventhub-connection"
  value        = azurerm_eventhub_authorization_rule.anomalies_send.primary_connection_string
  key_vault_id = azurerm_key_vault.main.id
  tags         = local.tags
}
