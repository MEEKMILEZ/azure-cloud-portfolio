# 09 — AI-driven operational intelligence + DR validation

## The problem this solves

**In a hospital:** Your IT team monitors dozens of servers and clinical systems. Azure Monitor fires hundreds of alerts every day. Most are noise — a brief CPU spike, a routine restart. But buried in that noise is the one alert that means a backup system is failing. Nobody catches it in time.

**In a warehouse:** Sensors on conveyor belts, cold storage units, and forklifts send thousands of status updates per hour. Equipment failure rarely announces itself loudly — it shows up as a gradual temperature creep, a subtle vibration change, a small RPM drop. By the time a human notices, the conveyor is down and shipments are delayed.

**The shared root cause:** Too many alerts, not enough signal. And a DR (disaster recovery) plan that looks great on paper but has never actually been tested.

---

## What this project builds

An end-to-end AI operations pipeline on Azure that:

1. **Ingests simulated sensor data** from warehouse equipment and clinical IT systems via Azure IoT Hub
2. **Detects anomalies in real time** using Azure Stream Analytics — flagging unusual patterns before they become outages
3. **Triages every alert with AI** using Azure OpenAI — classifying severity, suppressing noise, and writing a plain-English incident summary
4. **Routes actionable alerts** via Logic Apps to email or Microsoft Teams
5. **Validates DR readiness weekly** using an Automation Runbook that simulates a failover and measures whether systems recover within the promised RTO/RPO window
6. **Generates an AI-narrated DR health report** stored to Azure Blob Storage — the kind of document a compliance officer or ops manager can actually read

---

## Tech stack

| What it does | Azure service |
|---|---|
| Receives device messages | Azure IoT Hub |
| Detects anomalies in real time | Azure Stream Analytics |
| Classifies and explains alerts | Azure OpenAI (GPT-4o-mini) |
| Routes and delivers notifications | Azure Logic Apps |
| Runs weekly DR validation | Azure Automation Runbooks |
| Stores AI-generated reports | Azure Blob Storage |
| Centralizes all logs | Azure Log Analytics |
| Keeps secrets safe | Azure Key Vault |
| Builds all infrastructure | Terraform |

---

## Project structure

```
09-ai-ops-intelligence/
├── terraform/          # All Azure infrastructure as code
├── scripts/            # Python simulator + AI triage function + PowerShell DR runbook
├── prompts/            # OpenAI system prompts for alert triage and DR reports
└── screenshots/        # Walkthrough images for LinkedIn and documentation
```

---

## How to deploy

```bash
# 1. Clone the repo and navigate to this project
cd 09-ai-ops-intelligence/terraform

# 2. Copy the example variables file and fill in your values
cp terraform.tfvars.example terraform.tfvars

# 3. Initialise Terraform (downloads the Azure plugin)
terraform init

# 4. Preview what will be created
terraform plan

# 5. Deploy to Azure
terraform apply
```

---

## Industries targeted

This project is deliberately designed to resonate with two high-demand hiring verticals:

- **Healthcare IT** — alert fatigue in clinical environments, HIPAA-adjacent DR validation, compliance-ready reporting
- **Supply chain / distribution** — warehouse equipment monitoring, predictive failure signals, operational continuity planning

---

## Portfolio context

Part of the [MEEKMILEZ/azure-cloud-portfolio](https://github.com/MEEKMILEZ/azure-cloud-portfolio) series — real-world Azure problems solved with production-grade infrastructure.

Previous project: [08-cloud-cost-watchdog](../08-cloud-cost-watchdog)
