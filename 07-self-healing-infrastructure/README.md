# Project 7: Self-Healing Infrastructure with Infrastructure as Code

## Overview

This project deploys a complete Azure environment from a single Bicep template, sets up real-time monitoring with alert rules, and implements automated remediation runbooks that detect and fix infrastructure problems without human intervention. When a VM goes down, the system restarts it. When CPU spikes, the system scales the VM to a larger size. The entire workflow runs automatically: detect the problem, fix it, and notify the admin by email.

## Architecture

```
Bicep Template (Infrastructure as Code)
    |
    v deploys
VNet + NSG + VM + Storage Account + Public IP
    |
    v emits metrics
Azure Monitor + Alert Rules (CPU > 85%, VM stopped, Disk > 90%)
    |
    v triggers
Automation Runbooks (auto-restart VM, scale up VM, disk cleanup)
    |
    v notifies
Logic App --> Email Notification (alert fired, fix applied, status update)
    |
    v fixes
Infrastructure heals itself automatically
```

## Technologies Used

- Azure Bicep (Infrastructure as Code)
- Azure Automation (PowerShell Runbooks)
- Azure Monitor (Metric Alerts, Activity Log Alerts)
- Azure Logic Apps (Email Notification Workflow)
- Managed Identity (Credential-free Authentication)
- Azure RBAC (Role-Based Access Control)
- Azure Cloud Shell (PowerShell Deployment)

## Resource Naming

| Resource | Name |
|----------|------|
| Resource Group | RG-SelfHealing |
| Virtual Network | vnet-selfheal |
| Subnet | subnet-workload |
| NSG | nsg-workload |
| VM | vm-workload |
| Public IP | pip-workload |
| Storage Account | stgselfheal[unique] |
| Automation Account | aa-selfheal |
| Logic App | la-selfheal-notify |
| Action Groups | ag-selfheal, ag-scaleup |

## Deployment

**Region:** East US  
**Subscription:** Pay-As-You-Go  
**Deployment Method:** Azure Cloud Shell (PowerShell)  
**VM Size:** Standard_D2s_v3 (scales to D4s_v3 automatically)

### Phase 1: Infrastructure as Code (Bicep Deployment)

All infrastructure was deployed from a single Bicep template file (main.bicep) instead of manually creating each resource through the portal. The template defines a Virtual Network with one subnet, a Network Security Group with RDP and HTTP rules, a Windows Server 2022 VM, a Storage Account for boot diagnostics, and a Public IP address for remote access.

![Resource Group Created](01-resource-group-created.png)

![Bicep Template in Cloud Shell Editor](02-bicep-template-cloudshell.png)

![Bicep Deployment Succeeded](03-bicep-deployment-succeeded.png)

![All Resources Deployed](04-all-resources-deployed.png)

### Phase 2: Monitoring and Alert Rules

Three alert rules were configured to watch the VM around the clock:

| Alert Rule | Type | Trigger Condition |
|------------|------|-------------------|
| alert-high-cpu | Metric Alert | Average CPU > 85% for 5 minutes |
| alert-vm-stopped | Activity Log Alert | VM deallocated or stopped |
| alert-high-disk | Metric Alert | OS Disk Bandwidth > 90% for 5 minutes |

Each alert is connected to an action group that triggers the appropriate automation runbook and sends an email notification.

![Action Group Created](05-action-group-created.png)

![CPU Alert Rule Created](06-cpu-alert-rule-created.png)

![VM Stopped Alert Created](07-vm-stopped-alert-created.png)

![Disk Alert Created](08-disk-alert-created.png)

![All Alert Rules in Portal](09-all-alert-rules-portal.png)

### Phase 3: Self-Healing Automation Runbooks

Three PowerShell runbooks handle automated remediation:

**Restart-VM:** Checks if the VM is stopped and starts it back up automatically. Uses managed identity for authentication so no credentials are stored in the script.

**ScaleUp-VM:** Checks the current VM size and upgrades it from Standard_D2s_v3 to Standard_D4s_v3 when CPU is consistently high. Stops the VM, resizes it, and starts it again.

**Cleanup-Disk:** Runs disk cleanup commands on the VM using Invoke-AzVMRunCommand. Clears temp files and reports free space recovered.

All runbooks authenticate using the Automation Account's system-assigned managed identity with Contributor role on the resource group.

![Automation Account Created](10-automation-account-created.png)

![RBAC Role Assigned](11-rbac-role-assigned.png)

![Modules Imported](12-modules-imported.png)

![Restart Runbook Published](13-restart-runbook-published.png)

![ScaleUp Runbook Published](14-scaleup-runbook-published.png)

![Cleanup Runbook Published](15-cleanup-runbook-published.png)

![Alerts Linked to Runbooks](16-alerts-linked-to-runbooks.png)

### Phase 4: Notification Pipeline

A Logic App (la-selfheal-notify) sends email notifications when alerts fire and remediation actions are taken. The Logic App uses an Office 365 Outlook connector to deliver emails with details about which alert triggered and what action was taken.

![Logic App Created](17-logic-app-created.png)

![Logic App Workflow](18-logic-app-workflow.png)

### Phase 5: Testing

**Test 1: VM Auto-Restart**

Manually stopped the VM using Stop-AzVM. The Activity Log alert detected the VM was deallocated. The alert triggered the Restart-VM runbook through the action group. The runbook authenticated with managed identity and started the VM. VM came back online without any manual intervention. Email notification was received confirming the auto-restart.

![VM Stopped Manually](19-vm-stopped-manually.png)

![VM Auto-Restarted](20-vm-auto-restarted.png)

![Restart Runbook Output](21-restart-runbook-output.png)

**Test 2: CPU Spike and Auto Scale-Up**

Connected to the VM via RDP and ran CPU stress test using PowerShell infinite loops. CPU reached 100% utilization. After 5 minutes, the CPU alert fired. The ScaleUp-VM runbook triggered automatically. VM was stopped, resized from D2s_v3 to D4s_v3, and restarted.

![CPU Alert Action Groups](22-cpu-alert-action-groups.png)

![CPU Spike Detected](23-cpu-spike-detected.png)

![CPU Alert Fired](24-cpu-alert-fired.png)

![ScaleUp Job Completed](25-scaleup-job-completed.png)

![VM Scaled Up](26-vm-scaled-up.png)

**Automation Job History and Notifications**

![Automation Job History](27-automation-job-history.png)

![Action Group with Logic App](28-action-group-with-logic-app.png)

![Email Notification Received](29-email-notification-received.png)

## Troubleshooting

### Issue 1: microsoft.insights namespace not registered
- **Symptom:** Portal returned an error saying the subscription is not registered to use the namespace when creating an action group.
- **Cause:** The microsoft.insights resource provider was not registered in the subscription. This provider is required for Azure Monitor features like action groups, alert rules, and diagnostic settings.
- **Fix:** Ran `Register-AzResourceProvider -ProviderNamespace microsoft.insights` in Cloud Shell, waited for registration to complete, then retried successfully.

### Issue 2: Metric name "OS Disk Used Bytes" does not exist
- **Symptom:** Error "Couldn't find a metric named OS Disk Used Bytes" when creating the disk alert rule.
- **Cause:** Azure VMs do not expose a direct disk space usage metric. The available disk metrics are based on bandwidth, IOPS, and queue depth.
- **Fix:** Used `Get-AzMetricDefinition` to list all available metrics for the VM, then selected "OS Disk Bandwidth Consumed Percentage" with a 90% threshold as the closest alternative.

### Issue 3: Runbook jobs failed with "job definition was empty"
- **Symptom:** The Restart-VM runbook was triggered by the alert but failed immediately with "job definition was empty."
- **Cause:** The runbook script content was not saved properly when using `Out-File` in Cloud Shell. The file encoding was incompatible with Azure Automation.
- **Fix:** Re-created the script file using `Set-Content` with `-Encoding UTF8` and re-imported the runbook with the `-Published` flag. All subsequent jobs completed successfully.

### Issue 4: Logic App email delivery failed to Hotmail/Outlook
- **Symptom:** Email delivery failed with "A communication failure occurred during the delivery of this message." Outlook mail protection servers rejected the message.
- **Cause:** The Office 365 Outlook connector's authentication token expired, causing the email to be rejected by Outlook's spam filter.
- **Fix:** Removed and re-added the Outlook.com connector in the Logic App designer, re-authenticated with fresh credentials, and email delivery worked on all subsequent tests.

## Cost

- VM (Standard_D2s_v3): approximately $2-3 for a few hours of runtime
- Storage Account: minimal (pennies)
- Automation Account and Logic App: free tier
- Total project cost: under $5

## Cleanup

```powershell
Remove-AzResourceGroup -Name RG-SelfHealing -Force
```
