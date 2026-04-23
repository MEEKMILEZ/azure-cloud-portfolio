# 09 — AI Ops Intelligence: Automated Anomaly Detection and DR Validation

## The Problem

In a modern hospital, the IT infrastructure that keeps patients safe runs 24/7 — EHR application servers, medical imaging systems, clinical networks, and backup storage. When something goes wrong, the difference between a 2-minute response and a 20-minute response can determine whether a surgeon can access imaging, whether a nurse can pull up a patient's medication history, or whether a critical system stays online during a procedure.

Healthcare IT downtime costs an estimated $7,500 to $8,000 per minute. A single hospital's Azure environment generates hundreds of monitoring alerts per day. Most are noise — a CPU spike during a scheduled backup, a temperature reading that corrected itself, a network blip that resolved in seconds. The three alerts that actually matter get buried underneath the other 397.

The typical response is manual triage: an on-call engineer reads through a wall of alerts, decides what to investigate, and escalates based on gut feel. In healthcare, this is unacceptable. A critical alert buried under noise means delayed care. A false positive means the team stops trusting the monitoring system altogether. Both outcomes put patients at risk.

Separately, disaster recovery validation in healthcare IT is treated as a compliance checkbox — tested once a quarter at best, with results that nobody reads until an actual outage happens. By then, it's too late.

## The Solution

I built an AI-driven operational intelligence system designed specifically for healthcare IT infrastructure monitoring. Device telemetry flows from simulated clinical servers and medical systems into Azure IoT Hub every 10 seconds. Azure Stream Analytics watches the stream in real time. A Python triage function detects anomalies, sends each flagged device to Azure OpenAI, which reads the full signal pattern and writes a plain English verdict — what broke, how urgent, what the clinical IT team should do right now — then saves the report to Blob Storage and triggers an email via Logic Apps.

A separate Automation Runbook runs a DR validation drill every Monday at 6am UTC, measures actual RTO and RPO against configured targets, generates an AI-narrated health report, saves it to Blob Storage, and delivers it to the IT operations team automatically via Logic Apps.

The key difference from simple threshold alerting: when the clinical network switch showed packet loss alongside elevated CPU, the AI upgraded it from WARNING to CRITICAL — catching the correlated signal that a simple threshold rule would have missed. In a real hospital, that's the alert that tells you a switch is about to fail, not that it already has.

## Architecture

Two independent tracks run in parallel:

**Alert track:** IoT Hub → Event Hub → Stream Analytics → Triage Function → Azure OpenAI → Blob Storage → Logic App → Email

**DR track:** Automation Schedule → PowerShell Runbook → Azure OpenAI → Blob Storage → Logic App → Email

All infrastructure deployed via Terraform. No portal clicks for resource creation.

## Components

| Layer | Resource | Name | Purpose |
|---|---|---|---|
| **Ingestion** | IoT Hub | ioth-aiops-dev-1bpxtr | Receives device telemetry from 8 simulated clinical systems |
| | Event Hub Namespace | evhns-aiops-dev-1bpxtr | Routes messages between pipeline stages |
| **Processing** | Stream Analytics Job | asa-aiops-dev-1bpxtr | Real-time anomaly detection, auto-starts via Terraform |
| | Triage Function | triage-aiops | Python anomaly detection and OpenAI classification |
| | DR Runbook | runbook-dr-validation | Weekly failover simulation and AI report generation |
| **AI** | Azure OpenAI | oai-aiops-dev-1bpxtr | GPT-4o for alert classification and DR report generation |
| **Storage** | Storage Account | staiopsdev1bpxtr | Stores AI triage reports and DR health reports |
| | Key Vault | kv-aiops-dev-1bpxtr | Stores all connection strings and API keys |
| **Orchestration** | Logic App (Alert) | logic-alert-triage-aiops-dev-1bpxtr | HTTP trigger from triage function, sends email |
| | Logic App (DR) | logic-dr-validation-aiops-dev-1bpxtr | Weekly DR trigger, reads report, sends email |
| | Automation Account | aa-aiops-dev-1bpxtr | Hosts DR validation runbook with managed identity |
| **Monitoring** | Log Analytics | law-aiops-dev-1bpxtr | Centralized logging and diagnostics |
| | Action Group | ag-aiops-dev-1bpxtr | Email notifications for infrastructure alerts |
| | Monitor Alerts | alert-asa-errors, alert-iothub-drops | Pipeline health monitoring |

## Simulated Clinical Systems

| System | Metrics Monitored | Clinical Context |
|---|---|---|
| EHR application servers (×2) | CPU usage, network packet loss | Electronic Health Records access — downtime blocks all patient chart access |
| Medical imaging server | CPU usage, storage I/O | PACS/radiology imaging — delays affect surgical and diagnostic workflows |
| Clinical network switch | Packet loss %, CPU usage | Core hospital network — failure isolates entire departments |
| Pharmacy automation conveyors (×2) | Temperature, vibration | Automated medication dispensing — failures delay prescription fulfillment |
| Cold storage unit | Temperature | Vaccine and biologic refrigeration — temperature excursions destroy inventory |
| Loading dock forklift battery | Temperature, vibration | Supply chain equipment for pharmaceutical deliveries |

## Implementation

### Phase 1 — Foundation Infrastructure

All foundational resources deployed via Terraform: resource group, storage account with two blob containers (`alert-triage` and `ai-reports`), Key Vault with access policies, and Log Analytics workspace. One `terraform apply` creates everything.

![Resource Group Overview](./screenshots/01-resource-group-overview.png)
*Initial resource group rg-aiops-dev-1bpxtr created via Terraform, ready for the pipeline components.*

![Storage Containers](./screenshots/02-storage-containers.png)
*Storage account with two containers — alert-triage for AI triage JSON reports and ai-reports for DR validation health reports.*

![Key Vault Secret](./screenshots/03-key-vault-secret.png)
*Key Vault storing all connection strings and API keys as secrets. No credentials ever appear in code.*

![Resource Group Phase 2](./screenshots/04-phase2-resource-group.png)
*Resource group after Phase 2 deployment showing IoT Hub, Event Hub, and Stream Analytics added.*

### Phase 2 — Signal Ingestion Pipeline

IoT Hub routes all device messages to Event Hub via a custom endpoint. Stream Analytics reads from the Event Hub using a dedicated consumer group, applies the anomaly detection query, and flags devices that cross thresholds. The Stream Analytics job auto-starts via a Terraform `null_resource` that runs an Azure CLI command post-deployment — no manual portal interaction required.

![Stream Analytics Overview](./screenshots/05-stream-analytics-overview.png)
*Stream Analytics job asa-aiops-dev-1bpxtr in its initial configured state — inputs, outputs, and query all defined via Terraform.*

![IoT Hub Overview](./screenshots/06-iothub-overview.png)
*IoT Hub ioth-aiops-dev-1bpxtr with device registration and message routing to Event Hub configured.*

### Phase 3 — AI Triage Engine

Azure OpenAI deployed in East US with GPT-4o. The triage system prompt instructs the model to confirm or override the pre-classified severity, suppress noise for borderline readings, write a plain English summary readable by an IT operations manager, and recommend a specific action. The triage function reads fresh messages from the Event Hub, applies Python anomaly detection matching the Stream Analytics thresholds, and sends each flagged device to OpenAI.

![OpenAI Overview](./screenshots/07-openai-overview.png)
*Azure OpenAI resource oai-aiops-dev-1bpxtr active in East US, Standard tier, ready to receive alert classification requests.*

![OpenAI Model Deployment](./screenshots/08-openai-model-deployment.png)
*GPT-4o model deployment visible in the Azure AI Foundry portal.*

### Phase 4 — Orchestration, Monitoring and Notifications

Two Logic App workflows handle orchestration. The alert triage Logic App has an HTTP trigger — the triage function calls it directly after OpenAI analysis completes, eliminating polling delay. The DR validation Logic App runs on a weekly Monday schedule, reads the latest DR report from Blob Storage, and sends it to the IT operations team.

Azure Monitor alert rules watch the pipeline infrastructure — firing if Stream Analytics encounters errors or IoT Hub starts dropping messages.

![Logic App Alert Triage](./screenshots/09-logic-app-alert-triage.png)
*Logic App logic-alert-triage-aiops-dev-1bpxtr with HTTP trigger — called directly by the Python triage function after AI classification completes.*

![Action Group Email](./screenshots/11-action-group-email.png)
*Action group ag-aiops-dev-1bpxtr configured with email notification for infrastructure alerts.*

![Final Resource Group](./screenshots/12-final-resource-group-complete.png)
*Final resource group view showing all 14+ resources deployed and healthy — complete Terraform-managed infrastructure for the healthcare IT ops pipeline.*

### Phase 5 — DR Validation Runbook

The DR validation runbook authenticates via managed identity — no stored credentials anywhere. It checks storage accessibility, simulates a multi-step failover sequence measuring actual execution time, compares measured RTO and RPO against targets, calls Azure OpenAI to write a plain English health report, and saves the report to Blob Storage. The Logic App then picks it up and emails it automatically.

**RTO (Recovery Time Objective)** measures how long the system was unavailable during the simulated failover. In healthcare, a 30-minute RTO target means the clinical system must be back online within 30 minutes of a failure. **RPO (Recovery Point Objective)** measures how much data would have been lost — the gap between the last backup and the failover moment. An 8-minute RPO means at most 8 minutes of patient data could be lost.

![Automation Runbook](./screenshots/10-automation-runbook.png)
*Runbook runbook-dr-validation published in Automation Account aa-aiops-dev-1bpxtr, linked to weekly Monday 6am UTC schedule.*

![Stream Analytics Running](./screenshots/13-stream-analytics-running.png)
*Stream Analytics confirmed Running with 536 input events received — pipeline is live and flowing.*

![Runbook Completed](./screenshots/16-automation-runbook-completed.png)
*Runbook job completed successfully. Started 13:57, finished 13:59. RTO: 0.72 minutes (target: 30). RPO: 8 minutes (target: 15). Verdict: PASS.*

### Phase 6 — End-to-End Pipeline Test

The telemetry simulator sent 8 clinical systems × 59 cycles to IoT Hub. Anomaly injection fired every 4th cycle with amplified values — the EHR application servers hit 100% CPU with 4.7% packet loss, the medical imaging server hit 100% CPU, the clinical network switch on floor 2 showed 5.86% packet loss alongside elevated CPU.

The triage function read fresh messages from the Event Hub, applied anomaly detection, and sent 9 flagged systems to Azure OpenAI. The AI classified all 9 as CRITICAL — upgrading 5 of them from the pre-classified WARNING level because it caught correlated CPU and packet loss signals together. That correlation is what separates a network blip from an imminent application failure.

![Blob Storage Triage Reports](./screenshots/14-blob-storage-triage-reports.png)
*Blob Storage container alert-triage showing AI-generated critical triage reports saved automatically after the pipeline ran.*

![Logic App Triage Run History](./screenshots/20-logic-app-triage-run-history.png)
*Alert triage Logic App run history showing successful execution triggered by the Python triage function via HTTP call.*

![Triage Alert Email Received](./screenshots/19-triage-alert-email-received.png)
*AI triage alert email delivered to the on-call clinical IT engineer's inbox automatically.*

The DR validation report was delivered to the IT operations team inbox automatically:

![Blob DR Report](./screenshots/15-blob-dr-report.png)
*DR health report saved to Blob Storage under ai-reports/dr-reports/ with PASS prefix.*

![Logic App DR Email Sent](./screenshots/17-logic-app-dr-email-sent.png)
*Logic App run history showing all steps completed — weekly trigger, blob read, email sent.*

![DR Report Email](./screenshots/18-dr-report-email-received.png)
*AI-generated DR health report delivered to IT operations team email via Logic App. RTO: 0.72 minutes (target: 30). RPO: 8 minutes (target: 15). Verdict: PASS.*

## What This Automates

| Manual Process | Automated Solution |
|---|---|
| Escalate based on gut feel | AI confirms or upgrades severity based on correlated signals |
| Read through hundreds of alerts manually | Triage function detects anomalies and calls OpenAI automatically |
| Write incident summaries by hand | GPT-4o generates plain English verdict with recommended action |
| Run DR tests manually once per quarter | Automation Runbook runs every Monday at 6am UTC |
| Write DR reports for compliance audits | OpenAI generates human-readable report saved to Blob Storage |
| Email the team manually | Logic Apps deliver reports automatically to inbox |

## Troubleshooting and Lessons Learned

### Stream Analytics UNION ALL Query Not Supported
The original query used two separate SELECT INTO statements joined with UNION ALL. Azure Stream Analytics does not support writing to the same output from two separate SELECT statements in this pattern. Resolved by consolidating into a single SELECT with CASE expressions handling both high-CPU and high-packet-loss device types.

### Stream Analytics Output Events Remained Zero
After fixing the query syntax, output events remained zero despite 536+ input events. Root cause: the job was started with JobStartTime mode, meaning it only processes messages arriving after the job starts. Historical messages in the Event Hub backlog were counted as input events but their time windows had already closed. Resolved by changing the triage function to read directly from the Event Hub with a hard timer and applying Python anomaly detection, bypassing the output dependency.

### Logic App Blob Trigger Unreliable
Polling intervals and 403 Forbidden errors made the blob-based trigger unreliable. Redesigned the alert triage Logic App to use an HTTP trigger called directly by the Python triage function after OpenAI analysis completes — deterministic delivery, no polling.

### DR Runbook Missing Key Vault Name
The runbook failed on first execution because the KEY_VAULT_NAME environment variable was empty in the Automation Account runtime. Resolved by passing KeyVaultName as an explicit parameter when starting the runbook job.

### IoT Hub Rebuilding on Every Terraform Apply
Terraform detected drift on the min_tls_version attribute that Azure sets by default. Fixed by adding it to the lifecycle ignore_changes block in iothub.tf.

### GPT-4o-mini Version Retired
The gpt-4o-mini version 2024-07-18 model was deprecated on March 31, 2026. Resolved by switching to gpt-4o version 2024-11-20.

## Technologies Used

Terraform · Azure IoT Hub · Azure Event Hub · Azure Stream Analytics · Azure OpenAI (GPT-4o) · Azure Automation · PowerShell · Python · Azure Logic Apps · Azure Blob Storage · Azure Key Vault · Azure Monitor · Azure Log Analytics · Managed Identity · Azure RBAC

---

> **Note:** The architecture is industry-agnostic. The same pipeline supports warehouse and distribution monitoring, manufacturing equipment telemetry, and data center infrastructure with different simulated devices and context-specific AI prompts.
