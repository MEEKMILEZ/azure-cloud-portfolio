"""
Alert Triage Function — Project 09 AI Ops Intelligence
-------------------------------------------------------
This script reads flagged anomalies from the Azure Event Hub
(the ones Stream Analytics detected as suspicious), sends each
one to Azure OpenAI for classification, and saves the AI-generated
triage result to Azure Blob Storage.

In plain English: it picks up the flagged alerts, asks the AI
"what does this mean and what should we do?", then files the
answer away in the reports folder.

Run this script manually or trigger it from Logic Apps.
"""

import json
import os
import time
from datetime import datetime, timezone
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.eventhub import EventHubConsumerClient
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

# ─────────────────────────────────────────────
# CONFIGURATION
# All secrets come from Key Vault — nothing
# sensitive is stored in this file.
# ─────────────────────────────────────────────
KEY_VAULT_URL = os.environ.get("KEY_VAULT_URL")
MAX_MESSAGES = int(os.environ.get("MAX_MESSAGES", "50"))

def get_secret(client: SecretClient, name: str) -> str:
    """Retrieve a secret from Azure Key Vault."""
    return client.get_secret(name).value

def load_prompt(filename: str) -> str:
    """Load the system prompt from the prompts folder."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, "..", "prompts", filename)
    with open(prompt_path, "r") as f:
        return f.read()

def triage_alert(openai_client: AzureOpenAI, model: str, system_prompt: str, alert_data: dict) -> dict:
    """
    Send one alert to OpenAI and get back a triage decision.
    Returns the parsed JSON response from the AI.
    """
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(alert_data)}
            ],
            temperature=0.2,   # Low temperature = more consistent, less creative
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        result["original_alert"] = alert_data
        result["processed_at"] = datetime.now(timezone.utc).isoformat()
        return result

    except Exception as e:
        return {
            "final_severity": "ERROR",
            "confidence": "none",
            "summary": f"Triage function failed to process this alert: {str(e)}",
            "recommended_action": "Check triage function logs for details.",
            "original_alert": alert_data,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

def save_triage_result(blob_client: BlobServiceClient, container: str, result: dict):
    """
    Save the AI triage result to Blob Storage as a JSON file.
    The filename includes the device ID and timestamp so results
    are easy to find and never overwrite each other.
    """
    device_id = result.get("original_alert", {}).get("deviceId", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    severity = result.get("final_severity", "UNKNOWN").lower()
    blob_name = f"{severity}/{device_id}-{timestamp}.json"

    container_client = blob_client.get_container_client(container)
    container_client.upload_blob(
        name=blob_name,
        data=json.dumps(result, indent=2),
        overwrite=True
    )
    print(f"  Saved: {blob_name}")
    return blob_name

def main():
    print("=" * 60)
    print("Alert Triage Function starting...")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Connect to Key Vault
    credential = DefaultAzureCredential()
    kv_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)

    print("Retrieving secrets from Key Vault...")
    eventhub_connection = get_secret(kv_client, "anomaly-eventhub-connection")
    storage_connection  = get_secret(kv_client, "storage-connection-string")
    openai_endpoint     = get_secret(kv_client, "openai-endpoint")
    openai_key          = get_secret(kv_client, "openai-key")

    # Set up clients
    openai_client = AzureOpenAI(
        azure_endpoint=openai_endpoint,
        api_key=openai_key,
        api_version="2024-02-01"
    )
    blob_client = BlobServiceClient.from_connection_string(storage_connection)

    # Load the triage system prompt
    system_prompt = load_prompt("alert-triage.md")
    print("System prompt loaded.")

    # Read anomalies from Event Hub and triage each one
    alerts_processed = 0
    alerts_critical  = 0
    alerts_suppressed = 0

    print(f"\nReading up to {MAX_MESSAGES} anomalies from Event Hub...")

    def on_event(partition_context, event):
        nonlocal alerts_processed, alerts_critical, alerts_suppressed

        if alerts_processed >= MAX_MESSAGES:
            return

        try:
            alert_data = json.loads(event.body_as_str())
            device_id  = alert_data.get("deviceId", "unknown")
            severity   = alert_data.get("severity", "UNKNOWN")

            print(f"\n[{alerts_processed + 1}] Device: {device_id} | Pre-classified: {severity}")

            # Send to OpenAI for triage
            result = triage_alert(openai_client, "gpt-4o-mini", system_prompt, alert_data)
            final_severity = result.get("final_severity", "UNKNOWN")

            print(f"  AI verdict: {final_severity} (confidence: {result.get('confidence')})")
            print(f"  Summary: {result.get('summary', '')[:100]}...")

            # Save result to Blob Storage
            save_triage_result(blob_client, "alert-triage", result)

            alerts_processed += 1
            if final_severity == "CRITICAL":
                alerts_critical += 1
            if final_severity in ("SUPPRESSED", "INFO"):
                alerts_suppressed += 1

            partition_context.update_checkpoint()

        except Exception as e:
            print(f"  Error processing event: {e}")

    # Connect to the anomalies Event Hub and read messages
    consumer = EventHubConsumerClient.from_connection_string(
        conn_str=eventhub_connection,
        consumer_group="$Default",
        eventhub_name="evh-anomalies"
    )

    with consumer:
        consumer.receive(
            on_event=on_event,
            starting_position="-1",  # Read from the beginning of available messages
            max_wait_time=30
        )

    # Print summary
    print("\n" + "=" * 60)
    print("Triage complete.")
    print(f"  Total processed : {alerts_processed}")
    print(f"  Critical alerts : {alerts_critical}")
    print(f"  Suppressed/Info : {alerts_suppressed}")
    print(f"  Actionable      : {alerts_processed - alerts_suppressed}")
    print("=" * 60)

if __name__ == "__main__":
    if not KEY_VAULT_URL:
        print("ERROR: KEY_VAULT_URL environment variable is not set.")
        print("Set it like this:")
        print("  $env:KEY_VAULT_URL = 'https://kv-aiops-dev-1bpxtr.vault.azure.net/'")
    else:
        main()
