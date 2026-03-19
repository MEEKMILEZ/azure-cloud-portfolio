# Azure Security Monitoring & SIEM Implementation (Microsoft Sentinel)

## 📋 Overview

This project implements a centralized security monitoring and incident response pipeline in Microsoft Azure. It simulates a real-world Security Operations (SOC) workflow by collecting telemetry, detecting suspicious activity, and triggering automated responses.

The solution integrates multiple Azure services to provide end-to-end visibility, threat detection, and response automation across cloud infrastructure.

---

## 🧩 The Problem

Organizations often lack centralized visibility into their cloud environments. Logs are distributed across multiple services, making it difficult to detect threats early or respond efficiently.

Common challenges include:
- Limited visibility into infrastructure and user activity  
- Open management ports increasing attack surface  
- Delayed or manual incident response  
- Lack of automated threat detection and alerting  

Without a unified monitoring system, security teams operate reactively instead of proactively.

---

## ⚙️ The Solution

A layered security monitoring pipeline was designed and implemented using Azure-native tools:

- Centralized telemetry collection using Log Analytics  
- Advanced threat protection with Microsoft Defender for Cloud  
- Reduced attack surface using Just-in-Time (JIT) VM access  
- SIEM-based detection and incident management using Microsoft Sentinel  
- Automated incident response using Logic App playbooks  

This architecture enables continuous monitoring, real-time detection, and automated response to security events.

---

## 🏗️ Architecture

**Resources Deployed:**

Azure Virtual Machine (myVM) · Log Analytics Workspace · Storage Account · Data Collection Rule (DCR) · Microsoft Defender for Servers Plan 2 · Just-in-Time VM Access Policy · Microsoft Sentinel · Azure Activity Data Connector · Analytics Rule · Automated Playbook (Logic App)

**Flow:**

VM telemetry → Data Collection Rule → Log Analytics Workspace → Microsoft Sentinel → Analytics Rules → Automated Playbook Response

---

## 🔧 Core Implementation

### Monitoring & Telemetry Collection
- Deployed a virtual machine (**myVM**) as the monitored workload  
- Created a **Log Analytics Workspace** for centralized log ingestion  
- Configured a **Data Collection Rule (DCR)** to collect CPU, memory, disk, and network metrics  
- Provisioned a **storage account** for diagnostics and log storage  

### Threat Protection
- Enabled **Microsoft Defender for Servers Plan 2**  
- Added vulnerability assessment and enhanced threat detection capabilities  

### Access Control & Hardening
- Implemented **Just-in-Time (JIT) VM access**  
- Restricted management ports to minimize attack surface  
- Validated secure access workflow through time-bound access requests  

### Detection & Automated Response (SIEM)
- Deployed **Microsoft Sentinel** on top of the Log Analytics workspace  
- Connected **Azure Activity logs** for subscription-level monitoring  
- Created **analytics rules** to detect suspicious behavior  
- Built an **automated playbook (Logic App)** to respond to incidents  
- Validated end-to-end detection → incident creation → automated response workflow  

---

## 📈 Impact

- Centralized visibility across infrastructure and activity logs  
- Reduced attack surface through Just-in-Time access controls  
- Automated detection of suspicious activities using SIEM rules  
- Faster incident response through Logic App automation  
- Transition from reactive to proactive security operations  

---

## 🔍 Key Learnings

- Security monitoring is a layered pipeline, not a single tool  
- Data Collection Rules provide granular control over telemetry ingestion  
- Microsoft Defender enhances security posture with proactive threat detection  
- Just-in-Time access significantly reduces exposure to attacks  
- Microsoft Sentinel enables real-time detection and incident management  
- Automation is critical for scalable and efficient security operations  

---

## 📊 Results

- ✅ Virtual machine deployed and fully monitored  
- ✅ Centralized logging via Log Analytics Workspace  
- ✅ Microsoft Defender for Servers Plan 2 enabled  
- ✅ Just-in-Time VM access configured and validated  
- ✅ Microsoft Sentinel deployed with active data connectors  
- ✅ Analytics rules and automated playbooks operational  
- ✅ Successful detection of JIT policy deletion event  

---

## 📸 Screenshots

### Virtual Machine Deployment
![VM Created](./01-vm-created.png)

### Log Analytics Workspace
![Log Analytics](./02-log-analytics-workspace.png)

### Storage Account Configuration
![Storage Account](./03-storage-account.png)

### Data Collection Rule Setup
![DCR Created](./04-dcr-created.png)

### Microsoft Defender Enabled
![Defender Enabled](./05-defender-enabled.png)

### Just-in-Time Access Configuration
![JIT Enabled](./06-jit-enabled.png)

### JIT Access Request Approved
![JIT Access Granted](./07-jit-access-granted.png)

### Microsoft Sentinel Deployment
![Sentinel Added](./08-sentinel-added.png)

### Azure Activity Data Connector
![Activity Connector](./09-activity-connector.png)

### Analytics Rule Configuration
![Analytics Rule](./10-analytics-rule.png)

### Automated Playbook Deployment
![Playbook Deployed](./11-playbook-deployed.png)

### Custom Alert with Automation
![Custom Alert](./12-custom-alert-automation.png)

### Incident Detection in Sentinel
![Incident Created](./13-incident-created.png)

---

## 🔗 Related Certification Topics

- AZ-500: Manage security operations  
- AZ-500: Configure threat protection  
- AZ-104: Monitor and maintain Azure resources  
- SC-200: Mitigate threats using Microsoft Sentinel  
**Paschal Nnenna** · Cloud Administrator · [GitHub](https://github.com/MEEKMILEZ) · [LinkedIn](https://linkedin.com/in/paschal-nnenna)
