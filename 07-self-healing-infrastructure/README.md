# 07 — Self-Healing Infrastructure with Infrastructure as Code

## The Problem

When a VM crashes, runs out of CPU, or fills its disk in our environment, nobody knows until a user complains or someone happens to check the portal. The admin then has to manually log in, diagnose the issue, restart or resize the VM, and send an update to the team. If it happens at 2 AM or over a weekend, the system stays broken until someone notices. There is no automated detection, no automated fix, and no automated notification.

On top of that, every resource in the environment was created manually through the portal. There is no record of what was deployed or how it was configured. If something breaks badly enough that it needs to be rebuilt, the admin has to remember every setting and recreate it by hand.

## The Solution

I built a self-healing infrastructure system that deploys the entire environment from a single code file (Bicep template), monitors it in real time, automatically fixes problems when they happen, and sends an email to the team when a fix is applied. No human intervention required.

## Architecture

```
Bicep Template (Infrastructure as Code)
        ↓
Deployed Infrastructure (VNet, NSG, VM, Storage, Public IP)
        ↓
Azure Monitor + Alert Rules (CPU > 85%, VM stopped, Disk > 90%)
        ↓
Automation Runbooks (auto-restart VM, scale up VM, disk cleanup)
        ↓
Logic App → Email Notification (alert fired, fix applied, team notified)
```

## Components

| Resource | Name | Purpose |
|---|---|---|
| Resource Group | RG-SelfHealing | Contains all project resources |
| Virtual Network | vnet-selfheal | Network with one subnet and NSG |
| Virtual Machine | vm-workload | Windows Server 2022 workload being monitored |
| Storage Account | stgselfheal[unique] | Boot diagnostics storage |
| Automation Account | aa-selfheal | Hosts PowerShell runbooks with managed identity |
| Runbook | Restart-VM | Detects stopped VM and starts it automatically |
| Runbook | ScaleUp-VM | Resizes VM from D2s_v3 to D4s_v3 under high CPU |
| Runbook | Cleanup-Disk | Clears temp files when disk usage is high |
| Logic App | la-selfheal-notify | Sends email notification after remediation |
| Action Groups | ag-selfheal, ag-scaleup | Links alerts to runbooks and notifications |

## What This Automates

| Manual Process | Automated Solution |
|---|---|
| Check if VMs are running manually | Alert detects VM stopped, runbook restarts it |
| Monitor CPU usage in the portal | Alert fires at 85%, runbook scales VM up |
| Log in to clean up disk space | Runbook clears temp files via remote command |
| Email the team about what happened | Logic App sends notification automatically |
| Rebuild environment from memory | Bicep template redeploys everything from code |

## Implementation

### Phase 1 — Infrastructure as Code (Bicep Deployment)

Deployed all resources from a single Bicep template file (main.bicep) via Azure Cloud Shell. The template defines the VNet, subnet, NSG with RDP and HTTP rules, Windows Server 2022 VM (Standard_D2s_v3), storage account, and public IP. One command deploys the entire environment.

![Resource Group Created](./01-resource-group-created.png)

![Bicep Template in Cloud Shell Editor](./02-bicep-template-cloudshell.png)

![Bicep Deployment Succeeded](./03-bicep-deployment-succeeded.png)

![All Resources Deployed](./04-all-resources-deployed.png)

### Phase 2 — Monitoring and Alert Rules

Created an action group with email notification, then configured three alert rules to watch the VM continuously. The CPU alert fires when average usage exceeds 85% for 5 minutes. The VM stopped alert fires when the VM is deallocated. The disk alert fires when OS disk bandwidth consumption exceeds 90%.

![Action Group Created](./05-action-group-created.png)

![CPU Alert Rule Created](./06-cpu-alert-rule-created.png)

![VM Stopped Alert Created](./07-vm-stopped-alert-created.png)

![Disk Alert Created](./08-disk-alert-created.png)

![All Alert Rules in Portal](./09-all-alert-rules-portal.png)

### Phase 3 — Self-Healing Automation Runbooks

Created the Automation Account with system-assigned managed identity and Contributor role on the resource group. Imported Az.Accounts (v3.0.5) and Az.Compute (v8.3.0) with version pinning based on lessons learned from Project 6.

Three runbooks handle automated remediation. Restart-VM checks the VM power state and starts it if stopped. ScaleUp-VM stops the VM, resizes it from D2s_v3 to D4s_v3, and restarts it. Cleanup-Disk runs remote cleanup commands on the VM and reports recovered space.

Each runbook is linked to its corresponding alert through the action groups so remediation triggers automatically when an alert fires.

![Automation Account Created](./10-automation-account-created.png)

![RBAC Role Assigned](./11-rbac-role-assigned.png)

![Modules Imported](./12-modules-imported.png)

![Restart Runbook Published](./13-restart-runbook-published.png)

![ScaleUp Runbook Published](./14-scaleup-runbook-published.png)

![Cleanup Runbook Published](./15-cleanup-runbook-published.png)

![Alerts Linked to Runbooks](./16-alerts-linked-to-runbooks.png)

### Phase 4 — Notification Pipeline

Created a Logic App with an HTTP trigger and Office 365 Outlook connector. The Logic App is added to the action group so it fires alongside the runbook when an alert triggers. The email includes details about which alert fired and that remediation was executed.

![Logic App Created](./17-logic-app-created.png)

![Logic App Workflow](./18-logic-app-workflow.png)

### Phase 5 — Testing

**Test 1: VM Auto-Restart**

Stopped the VM manually using Stop-AzVM. The Activity Log alert detected the deallocation, triggered the Restart-VM runbook through the action group, and the VM came back online without any manual intervention. Email notification was received confirming the fix.

![VM Stopped Manually](./19-vm-stopped-manually.png)

![VM Auto-Restarted — Job Completed](./20-vm-auto-restarted.png)

![Restart Runbook Output](./21-restart-runbook-output.png)

**Test 2: CPU Spike and Auto Scale-Up**

Connected to the VM via RDP and ran PowerShell stress loops to push CPU to 100%. After 5 minutes the CPU alert fired, the ScaleUp-VM runbook triggered automatically, and the VM was resized from D2s_v3 to D4s_v3. The RDP session disconnected during resize which is expected.

![CPU Alert Action Groups](./22-cpu-alert-action-groups.png)

![CPU Spike at 100%](./23-cpu-spike-detected.png)

![CPU Alert Fired](./24-cpu-alert-fired.png)

![ScaleUp Job Completed](./25-scaleup-job-completed.png)

![VM Scaled Up to D4s_v3](./26-vm-scaled-up.png)

**Job History and Email Confirmation**

![Automation Job History — All Completed](./27-automation-job-history.png)

![Action Group with Logic App](./28-action-group-with-logic-app.png)

![Email Notification Received](./29-email-notification-received.png)

## Impact

- **Response time:** Problems detected and fixed in minutes instead of hours or days
- **Availability:** VM auto-restarts without waiting for an admin to notice
- **Scalability:** VM automatically upgrades when CPU is consistently overloaded
- **Repeatability:** Entire environment can be redeployed from one Bicep file in under 5 minutes
- **Cost:** Under $5 total for deployment, testing, and teardown
- **Security:** Zero stored credentials — managed identity handles all authentication

## Troubleshooting & Lessons Learned

### microsoft.insights Namespace Not Registered
When creating the first action group, the portal returned an error saying the subscription was not registered for the microsoft.insights namespace. This provider is required for all Azure Monitor features including action groups, alert rules, and diagnostic settings. Resolved by running `Register-AzResourceProvider -ProviderNamespace microsoft.insights` in Cloud Shell and waiting for registration to complete.

### Metric Name "OS Disk Used Bytes" Does Not Exist
The disk alert rule failed with "Couldn't find a metric named OS Disk Used Bytes." Azure VMs do not expose a direct disk space percentage metric. The available disk metrics are bandwidth, IOPS, and queue depth based. Resolved by using `Get-AzMetricDefinition` to list all available VM metrics, then selecting "OS Disk Bandwidth Consumed Percentage" with a 90% threshold.

### Runbook Jobs Failed With "Job Definition Was Empty"
The Restart-VM runbook was triggered by the alert but failed immediately with "job definition was empty." The runbook script content was not saved properly when using `Out-File` in Cloud Shell due to incompatible file encoding. Resolved by re-creating the script using `Set-Content` with `-Encoding UTF8` and re-importing with the `-Published` flag. All subsequent jobs completed successfully.

### Logic App Email Delivery Rejected by Outlook
Email delivery failed with "A communication failure occurred during the delivery of this message." Outlook's mail protection servers rejected the message because the Office 365 connector's authentication token had expired. Resolved by removing and re-adding the Outlook.com connector in the Logic App designer with fresh credentials. All subsequent emails delivered successfully.

## Technologies Used

Azure Bicep, Azure Automation, PowerShell, Azure Monitor, Alert Rules, Azure Logic Apps, Managed Identity, Azure RBAC, Azure Cloud Shell, Office 365 Outlook Connector
