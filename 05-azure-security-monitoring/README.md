# 05 — Azure Security Monitoring

## Overview

This project brings together four interconnected labs to build a complete security monitoring pipeline in Microsoft Azure. Starting with a monitored virtual machine and centralized log collection, it layers on advanced threat protection, just-in-time access controls, and a full SIEM deployment using Microsoft Sentinel. The goal was to simulate what a real-world security operations workflow looks like — from collecting telemetry to detecting incidents and automating responses.

Every organization needs visibility into what's happening across its infrastructure. This project demonstrates how to build that visibility from the ground up, using the same tools and techniques that cloud security teams rely on every day.

## Architecture

**Resources Deployed:**

Azure Virtual Machine (myVM) · Log Analytics Workspace · Storage Account · Data Collection Rule (DCR) · Microsoft Defender for Servers Plan 2 · Just-in-Time VM Access Policy · Microsoft Sentinel · Azure Activity Data Connector · Analytics Rule · Automated Playbook (Logic App)

**Flow:**

VM telemetry → Data Collection Rule → Log Analytics Workspace → Microsoft Sentinel → Analytics Rules → Automated Playbook Response

---

## Lab Breakdown

### Lab 08 — Monitoring Foundation

The foundation of any security monitoring setup is knowing what's happening on your machines. This lab focused on deploying the core infrastructure needed to collect and centralize telemetry data.

- Deployed **myVM** using PowerShell as the target machine to be monitored and protected
- Created a **Log Analytics workspace** to serve as the central hub for all log data
- Provisioned a **storage account** to hold diagnostic data
- Configured a **Data Collection Rule (DCR)** to collect CPU, memory, disk, and network metrics every 60 seconds

| # | Screenshot | Description |
|---|-----------|-------------|
| 1 | ![VM Created](screenshots/01-vm-created.png) | Deployed myVM using PowerShell to be monitored and protected. |
| 2 | ![Log Analytics](screenshots/02-log-analytics-workspace.png) | Created Log Analytics workspace to centralize log collection. |
| 3 | ![Storage Account](screenshots/03-storage-account.png) | Created storage account for diagnostic data. |
| 4 | ![DCR Created](screenshots/04-dcr-created.png) | Created DCR to collect CPU, Memory, Disk, and Network metrics every 60 seconds. |

---

### Lab 09 — Microsoft Defender for Cloud

With telemetry flowing, the next step was enabling advanced threat protection. Microsoft Defender for Servers Plan 2 adds vulnerability assessments, adaptive application controls, and real-time threat detection on top of the monitoring foundation.

- Enabled **Microsoft Defender for Servers Plan 2** for advanced threat protection across the subscription

| # | Screenshot | Description |
|---|-----------|-------------|
| 5 | ![Defender Enabled](screenshots/05-defender-enabled.png) | Enabled Microsoft Defender for Servers Plan 2 for advanced threat protection. |

---

### Lab 10 — Just-in-Time VM Access

Leaving management ports open around the clock is one of the most common attack vectors in cloud environments. Just-in-Time (JIT) access solves this by keeping ports closed by default and only opening them temporarily when access is explicitly requested and approved.

- Enabled **Just-in-Time VM access** to reduce the attack surface by locking down management ports
- Requested and was granted **temporary JIT access** to connect to the VM, demonstrating the approval workflow

| # | Screenshot | Description |
|---|-----------|-------------|
| 6 | ![JIT Enabled](screenshots/06-jit-enabled.png) | Enabled Just-in-Time VM access to reduce attack surface. |
| 7 | ![JIT Access Granted](screenshots/07-jit-access-granted.png) | Requested and granted temporary JIT access to connect to the VM. |

---

### Lab 11 — Microsoft Sentinel (SIEM)

This is where everything comes together. Microsoft Sentinel sits on top of the Log Analytics workspace and turns raw log data into actionable security intelligence. This lab covered connecting data sources, creating detection rules, deploying automated response playbooks, and validating that the entire pipeline works end-to-end.

- Added **Microsoft Sentinel** to the Log Analytics workspace for full SIEM capabilities
- Connected the **Azure Activity data connector** to monitor subscription-level activity
- Created an **analytics rule** to detect suspicious resource creation events
- Deployed an **automated playbook** (Logic App) to change incident severity on trigger
- Built a **custom alert with automated playbook response** to tie detection to action
- Validated the pipeline — **Sentinel caught a JIT policy deletion automatically**, confirming that the detection-to-incident workflow is fully operational

| # | Screenshot | Description |
|---|-----------|-------------|
| 8 | ![Sentinel Added](screenshots/08-sentinel-added.png) | Added Microsoft Sentinel to the Log Analytics workspace for full SIEM capabilities. |
| 9 | ![Activity Connector](screenshots/09-activity-connector.png) | Connected Azure Activity data connector to monitor subscription activity. |
| 10 | ![Analytics Rule](screenshots/10-analytics-rule.png) | Created analytics rule to detect suspicious resource creation. |
| 11 | ![Playbook Deployed](screenshots/11-playbook-deployed.png) | Deployed playbook to automate incident severity changes. |
| 12 | ![Custom Alert](screenshots/12-custom-alert-automation.png) | Created custom alert with automated playbook response. |
| 13 | ![Incident Created](screenshots/13-incident-created.png) | Incident detected — Sentinel caught the JIT policy deletion automatically. |

---

## Technologies Used

Microsoft Azure · Azure Virtual Machines · Log Analytics · Data Collection Rules · Microsoft Defender for Cloud · Just-in-Time VM Access · Microsoft Sentinel · Logic Apps · Azure Activity Connector · KQL (Kusto Query Language)

## Key Takeaways

This project reinforced that security monitoring isn't a single tool — it's a pipeline. Each lab built on the one before it, from basic telemetry collection all the way to automated incident response. The most rewarding part was seeing Sentinel catch the JIT policy deletion in real time without any manual intervention. That's the kind of end-to-end automation that separates a reactive security posture from a proactive one.

---

**Paschal Nnenna** · Cloud Administrator · [GitHub](https://github.com/MEEKMILEZ) · [LinkedIn](https://linkedin.com/in/paschal-nnenna)
