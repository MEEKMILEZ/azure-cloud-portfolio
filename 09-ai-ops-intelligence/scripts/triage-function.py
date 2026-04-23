"""
Alert Triage Function — Project 09 AI Ops Intelligence
-------------------------------------------------------
Reads device telemetry directly from evh-alerts Event Hub,
applies anomaly detection logic in Python, sends flagged alerts
to Azure OpenAI for plain-English classification, and saves
AI-generated triage reports to Azure Blob Storage.
"""

import json
import os
from datetime import datetime, timezone
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.eventhub import EventHubConsumerClient
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

KEY_VAULT_URL          = os.environ.get("KEY_VAULT_URL")
EVENTHUB_ALERTS_CONN   = os.environ.get("EVENTHUB_ALERTS_CONNECTION")
MAX_MESSAGES           = int(os.environ.get("MAX_MESSAGES", "200"))

def get_secret(client, name):
    return client.get_secret(name).value

def load_prompt(filename):
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, "..", "prompts", filename)
    with open(prompt_path, "r") as f:
        return f.read()

def is_anomalous(msg):
    industry = msg.get("industry", "")
    temp     = float(msg.get("temperature", 0) or 0)
    vib      = float(msg.get("vibration", 0) or 0)
    cpu      = float(msg.get("cpu_pct", 0) or 0)
    loss     = float(msg.get("packet_loss_pct", 0) or 0)

    if industry == "warehouse":
        if temp > 85 and vib > 0.8:
            return True, "CRITICAL"
        if temp > 75 or vib > 0.6:
            return True, "WARNING"
    elif industry == "healthcare":
        if cpu > 90 and loss > 3:
            return True, "CRITICAL"
        if cpu > 80 or loss > 2:
            return True, "WARNING"
    return False, "NORMAL"

def triage_alert(openai_client, model, system_prompt, alert_data):
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": json.dumps(alert_data)}
            ],
            temperature=0.2,
            max_tokens=500
        )
        text   = response.choices[0].message.content
        text   = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        result["original_alert"] = alert_data
        result["processed_at"]   = datetime.now(timezone.utc).isoformat()
        return result
    except Exception as e:
        return {
            "final_severity":     "ERROR",
            "confidence":         "none",
            "summary":            f"Triage failed: {e}",
            "recommended_action": "Check triage function logs.",
            "original_alert":     alert_data,
            "processed_at":       datetime.now(timezone.utc).isoformat()
        }

def save_result(blob_client, container, result):
    device_id = result.get("original_alert", {}).get("deviceId", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    severity  = result.get("final_severity", "UNKNOWN").lower()
    blob_name = f"{severity}/{device_id}-{timestamp}.json"
    container_client = blob_client.get_container_client(container)
    container_client.upload_blob(name=blob_name, data=json.dumps(result, indent=2), overwrite=True)
    return blob_name

def main():
    print("=" * 60)
    print("Alert Triage Function starting...")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    if not KEY_VAULT_URL:
        print("ERROR: KEY_VAULT_URL environment variable not set.")
        return

    if not EVENTHUB_ALERTS_CONN:
        print("ERROR: EVENTHUB_ALERTS_CONNECTION environment variable not set.")
        print("Run: $env:EVENTHUB_ALERTS_CONNECTION = '<connection string>'")
        return

    credential = DefaultAzureCredential()
    kv_client  = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)

    print("Retrieving secrets from Key Vault...")
    storage_connection = get_secret(kv_client, "storage-connection-string")
    openai_endpoint    = get_secret(kv_client, "openai-endpoint")
    openai_key         = get_secret(kv_client, "oai-aiops-dev-1bpxtr")

    openai_client = AzureOpenAI(
        azure_endpoint=openai_endpoint,
        api_key=openai_key,
        api_version="2024-02-01"
    )
    blob_client   = BlobServiceClient.from_connection_string(storage_connection)
    system_prompt = load_prompt("alert-triage.md")
    print("Clients ready.")

    # Read messages from evh-alerts
    all_messages = []

    def on_event(partition_context, event):
        if event is None:
            return
        if len(all_messages) >= MAX_MESSAGES:
            return
        try:
            body = event.body_as_str()
            if not body:
                return
            msg = json.loads(body)
            if isinstance(msg, dict) and msg.get("deviceId"):
                all_messages.append(msg)
                partition_context.update_checkpoint()
        except Exception:
            pass

    print(f"Reading up to {MAX_MESSAGES} messages from evh-alerts (20 second window)...")

    import threading
    consumer = EventHubConsumerClient.from_connection_string(
        conn_str=EVENTHUB_ALERTS_CONN,
        consumer_group="$Default",
        eventhub_name="evh-alerts"
    )

    def stop_consumer():
        consumer.close()

    timer = threading.Timer(20, stop_consumer)
    timer.start()
    try:
        consumer.receive(
            on_event=on_event,
            starting_position="@latest",
        )
    except Exception:
        pass
    finally:
        timer.cancel()

    print(f"Messages read: {len(all_messages)}")

    if not all_messages:
        print("\nNo messages found. Run simulate-telemetry.py first then retry.")
        return

    # Apply anomaly detection
    anomalies = []
    for msg in all_messages:
        flagged, severity = is_anomalous(msg)
        if flagged:
            msg["pre_classified_severity"] = severity
            anomalies.append(msg)

    print(f"Anomalies detected: {len(anomalies)} out of {len(all_messages)} messages")

    if not anomalies:
        print("\nNo anomalies found in messages. All readings were within normal range.")
        return

    # Triage with OpenAI
    processed = critical = suppressed = 0
    print(f"\nTriaging {min(len(anomalies), 10)} anomalies with Azure OpenAI gpt-4o-mini...")

    for alert in anomalies[:10]:
        device_id = alert.get("deviceId", "unknown")
        severity  = alert.get("pre_classified_severity")
        print(f"\n  [{processed+1}] Device: {device_id} | Pre-classified: {severity}")

        result    = triage_alert(openai_client, "gpt-4o-mini", system_prompt, alert)
        final_sev = result.get("final_severity", "UNKNOWN")
        print(f"  AI verdict  : {final_sev} (confidence: {result.get('confidence')})")
        print(f"  Summary     : {result.get('summary', '')[:120]}")
        print(f"  Action      : {result.get('recommended_action', '')[:100]}")

        blob_name = save_result(blob_client, "alert-triage", result)
        print(f"  Saved to    : {blob_name}")

        processed += 1
        if final_sev == "CRITICAL":
            critical += 1
        if final_sev in ("SUPPRESSED", "INFO"):
            suppressed += 1

    print("\n" + "=" * 60)
    print(f"  Total processed : {processed}")
    print(f"  Critical alerts : {critical}")
    print(f"  Suppressed/Info : {suppressed}")
    print(f"  Actionable      : {processed - suppressed}")
    print("=" * 60)

if __name__ == "__main__":
    main()
