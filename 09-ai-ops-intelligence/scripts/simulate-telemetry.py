"""
Telemetry Simulator — Project 09 AI Ops Intelligence
------------------------------------------------------
This script pretends to be warehouse sensors and hospital
servers sending data to Azure IoT Hub.

Most of the time it sends normal healthy readings.
Every so often it "breaks" a device on purpose — injecting
a spike or a slow degradation — so Stream Analytics has
something real to detect and flag.

Run this AFTER the Stream Analytics job is started.
"""

import json
import random
import time
import os
from datetime import datetime, timezone
from azure.iot.device import IoTHubDeviceClient, Message

# ─────────────────────────────────────────────
# DEVICE PROFILES
# Each device has a normal operating range.
# When anomaly_mode is triggered, values drift
# outside these ranges to simulate a real problem.
# ─────────────────────────────────────────────
WAREHOUSE_DEVICES = [
    {
        "device_id"  : "conveyor-motor-zone1",
        "type"       : "conveyor_motor",
        "normal_temp": 62.0,
        "normal_vib" : 0.35,
        "zone"       : "Zone 1"
    },
    {
        "device_id"  : "conveyor-motor-zone4",
        "type"       : "conveyor_motor",
        "normal_temp": 65.0,
        "normal_vib" : 0.38,
        "zone"       : "Zone 4"
    },
    {
        "device_id"  : "cold-storage-unit-a",
        "type"       : "cold_storage",
        "normal_temp": -18.0,
        "normal_vib" : 0.10,
        "zone"       : "Cold Store A"
    },
    {
        "device_id"  : "forklift-battery-03",
        "type"       : "forklift",
        "normal_temp": 28.0,
        "normal_vib" : 0.20,
        "zone"       : "Dock Area"
    }
]

HEALTHCARE_DEVICES = [
    {
        "device_id"    : "ehr-app-server-01",
        "type"         : "app_server",
        "normal_temp"  : 45.0,
        "normal_cpu"   : 55.0,
        "normal_loss"  : 0.1
    },
    {
        "device_id"    : "ehr-app-server-02",
        "type"         : "app_server",
        "normal_temp"  : 47.0,
        "normal_cpu"   : 60.0,
        "normal_loss"  : 0.1
    },
    {
        "device_id"    : "imaging-server-01",
        "type"         : "imaging_server",
        "normal_temp"  : 52.0,
        "normal_cpu"   : 70.0,
        "normal_loss"  : 0.2
    },
    {
        "device_id"    : "network-switch-floor2",
        "type"         : "network_switch",
        "normal_temp"  : 38.0,
        "normal_cpu"   : 30.0,
        "normal_loss"  : 0.05
    }
]

def generate_warehouse_reading(device: dict, inject_anomaly: bool = False) -> dict:
    """
    Generate one telemetry reading from a warehouse device.
    Normal readings have small random variation around the baseline.
    Anomaly readings spike the temperature and vibration significantly.
    """
    noise_temp = random.gauss(0, 1.5)
    noise_vib  = random.gauss(0, 0.02)

    if inject_anomaly:
        # Simulate bearing failure: temperature creeps up, vibration spikes
        anomaly_temp = random.uniform(20, 35)
        anomaly_vib  = random.uniform(0.3, 0.6)
    else:
        anomaly_temp = 0
        anomaly_vib  = 0

    temperature = round(device["normal_temp"] + noise_temp + anomaly_temp, 2)
    vibration   = round(max(0, device["normal_vib"] + noise_vib + anomaly_vib), 3)

    return {
        "deviceId"   : device["device_id"],
        "deviceType" : device["type"],
        "industry"   : "warehouse",
        "zone"       : device.get("zone", "unknown"),
        "temperature": temperature,
        "vibration"  : vibration,
        "status"     : "ANOMALY" if inject_anomaly else "NORMAL",
        "timestamp"  : datetime.now(timezone.utc).isoformat()
    }

def generate_healthcare_reading(device: dict, inject_anomaly: bool = False) -> dict:
    """
    Generate one telemetry reading from a healthcare IT device.
    Normal readings have small random variation.
    Anomaly readings spike CPU and packet loss to simulate an overloaded server.
    """
    noise_temp = random.gauss(0, 1.0)
    noise_cpu  = random.gauss(0, 3.0)
    noise_loss = random.gauss(0, 0.05)

    if inject_anomaly:
        anomaly_cpu  = random.uniform(25, 40)
        anomaly_loss = random.uniform(2.0, 5.0)
        anomaly_temp = random.uniform(10, 20)
    else:
        anomaly_cpu  = 0
        anomaly_loss = 0
        anomaly_temp = 0

    return {
        "deviceId"      : device["device_id"],
        "deviceType"    : device["type"],
        "industry"      : "healthcare",
        "temperature"   : round(device["normal_temp"] + noise_temp + anomaly_temp, 2),
        "cpu_pct"       : round(min(100, max(0, device["normal_cpu"] + noise_cpu + anomaly_cpu)), 2),
        "packet_loss_pct": round(max(0, device["normal_loss"] + noise_loss + anomaly_loss), 3),
        "status"        : "ANOMALY" if inject_anomaly else "NORMAL",
        "timestamp"     : datetime.now(timezone.utc).isoformat()
    }

def send_message(client: IoTHubDeviceClient, payload: dict):
    """Send one message to IoT Hub."""
    message = Message(json.dumps(payload))
    message.content_type     = "application/json"
    message.content_encoding = "utf-8"
    client.send_message(message)

def main():
    # Get the IoT Hub connection string
    # Set this environment variable before running:
    # $env:IOTHUB_DEVICE_CONNECTION_STRING = "HostName=...;DeviceId=...;SharedAccessKey=..."
    connection_string = os.environ.get("IOTHUB_DEVICE_CONNECTION_STRING")

    if not connection_string:
        print("ERROR: IOTHUB_DEVICE_CONNECTION_STRING environment variable not set.")
        print("\nTo get your connection string:")
        print("1. Go to portal.azure.com")
        print("2. Open your IoT Hub: ioth-aiops-dev-1bpxtr")
        print("3. Go to Devices > Add device > warehouse-sensor-01")
        print("4. Copy the Primary Connection String")
        print("5. Run: $env:IOTHUB_DEVICE_CONNECTION_STRING = '<paste here>'")
        return

    print("=" * 60)
    print("Telemetry Simulator starting...")
    print("Sending messages to IoT Hub every 10 seconds.")
    print("Press Ctrl+C to stop.")
    print("=" * 60)

    client = IoTHubDeviceClient.create_from_connection_string(connection_string)

    messages_sent = 0
    anomaly_cycle = 0  # Every 20 messages, inject an anomaly

    try:
        while True:
            anomaly_cycle += 1
            # Inject anomaly every 20th cycle — about 5% of readings
            inject_anomaly = (anomaly_cycle % 20 == 0)

            if inject_anomaly:
                print(f"\n[{messages_sent + 1}] INJECTING ANOMALY this cycle...")
            else:
                print(f"\n[{messages_sent + 1}] Normal cycle")

            # Send readings from all warehouse devices
            for device in WAREHOUSE_DEVICES:
                # Only inject anomaly into one random device per cycle
                is_anomaly_device = inject_anomaly and (device == random.choice(WAREHOUSE_DEVICES))
                payload = generate_warehouse_reading(device, is_anomaly_device)
                send_message(client, payload)
                status = "ANOMALY" if is_anomaly_device else "ok"
                print(f"  {device['device_id']}: temp={payload['temperature']}°C "
                      f"vib={payload['vibration']} [{status}]")

            # Send readings from all healthcare devices
            for device in HEALTHCARE_DEVICES:
                is_anomaly_device = inject_anomaly and (device == random.choice(HEALTHCARE_DEVICES))
                payload = generate_healthcare_reading(device, is_anomaly_device)
                send_message(client, payload)
                status = "ANOMALY" if is_anomaly_device else "ok"
                print(f"  {device['device_id']}: cpu={payload['cpu_pct']}% "
                      f"loss={payload['packet_loss_pct']}% [{status}]")

            messages_sent += 1
            print(f"\nTotal cycles sent: {messages_sent}. Waiting 10 seconds...")
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\nSimulator stopped.")
        print(f"Total cycles completed: {messages_sent}")
        client.disconnect()

if __name__ == "__main__":
    main()
