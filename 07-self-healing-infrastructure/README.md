# Self-Healing Cloud Infrastructure on Azure (Auto-Remediation System)

## The Problem

When a VM crashes, runs out of CPU, or fills its disk in our environment, nobody knows until a user complains or someone happens to check the portal. The admin then has to manually log in, diagnose the issue, restart or resize the VM, and send an update to the team. If it happens at 2 AM or over a weekend, the system stays broken until someone notices. There is no automated detection, no automated fix, and no automated notification.

On top of that, every resource in the environment was created manually through the portal. There is no record of what was deployed or how it was configured. If something breaks badly enough that it needs to be rebuilt, the admin has to remember every setting and recreate it by hand.

## The Solution

I built a self-healing infrastructure system that deploys the entire environment from a single code file (Bicep template), monitors it in real time, automatically fixes problems when they happen, and sends an email to the team when a fix is applied. No human intervention required.

## Architecture

![Architecture Diagram](./architecture-diagram.svg)

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

Instead of clicking through the Azure portal to create each resource one by one, the entire environment was defined in a single Bicep template file called main.bicep. This file describes the VNet, subnet, NSG with RDP and HTTP rules, a Windows Server 2022 VM (Standard_D2s_v3), a storage account for boot diagnostics, and a public IP address. One deployment command builds everything at once.

Started by creating the resource group in East US using Azure Cloud Shell (PowerShell).

![Resource Group Created](./01-resource-group-created.png)
*RG-SelfHealing resource group created in East US.*

Wrote the Bicep template in the Cloud Shell editor. The file defines all six resources and their dependencies in about 100 lines of code.

![Bicep Template in Cloud Shell Editor](./02-bicep-template-cloudshell.png)
*The main.bicep file open in Cloud Shell editor showing the infrastructure definition.*

Deployed the template using New-AzResourceGroupDeployment. The deployment took about 3 minutes to provision all resources.

![Bicep Deployment Succeeded](./03-bicep-deployment-succeeded.png)
*Deployment output showing ProvisioningState: Succeeded.*

Verified all resources were created by listing everything in the resource group.

![All Resources Deployed](./04-all-resources-deployed.png)
*All six resources created from the single Bicep template.*

### Phase 2 — Monitoring and Alert Rules

With the infrastructure running, the next step was setting up monitoring so the system can detect problems automatically. This involved creating action groups (contact lists that define who gets notified and what automation runs) and alert rules (conditions that trigger when something goes wrong).

Created the first action group with an email notification receiver. This group gets notified when alerts fire.

![Action Group Created](./05-action-group-created.png)
*Action group ag-selfheal created with email notification.*

Created a metric alert rule that fires when the VM's average CPU usage exceeds 85% for 5 consecutive minutes.

![CPU Alert Rule Created](./06-cpu-alert-rule-created.png)
*CPU alert rule configured with 85% threshold and 5-minute evaluation window.*

Created an Activity Log alert that fires when the VM is deallocated or stopped. Unlike metric alerts that watch performance numbers, Activity Log alerts watch for management operations like someone (or something) shutting down the VM.

![VM Stopped Alert Created](./07-vm-stopped-alert-created.png)
*Activity Log alert configured to detect VM deallocation events.*

Created a metric alert for disk pressure. Azure VMs do not expose a direct "disk space percentage" metric, so after researching available metrics using Get-AzMetricDefinition, I used OS Disk Bandwidth Consumed Percentage with a 90% threshold.

![Disk Alert Created](./08-disk-alert-created.png)
*Disk bandwidth alert rule configured with 90% threshold.*

Verified all three alert rules are active and monitoring the VM from the Azure Monitor portal.

![All Alert Rules in Portal](./09-all-alert-rules-portal.png)
*All three alert rules visible and enabled in Azure Monitor.*

### Phase 3 — Self-Healing Automation Runbooks

This is the core of the project. Three PowerShell runbooks were created to automatically fix problems detected by the alert rules. Each runbook authenticates using the Automation Account's managed identity so no passwords or credentials are stored anywhere in the code.

Created the Automation Account with a system-assigned managed identity enabled.

![Automation Account Created](./10-automation-account-created.png)
*Automation account aa-selfheal created with managed identity enabled.*

Assigned the Contributor role to the managed identity on the resource group. This gives the runbooks permission to restart VMs, resize them, and run commands on them.

![RBAC Role Assigned](./11-rbac-role-assigned.png)
*Contributor role assigned to the managed identity on RG-SelfHealing.*

Imported the required PowerShell modules with version pinning. Based on lessons from Project 6, I used Az.Accounts v3.0.5 and Az.Compute v8.3.0 to avoid compatibility issues with the Automation runtime.

![Modules Imported](./12-modules-imported.png)
*Both Az.Accounts and Az.Compute modules showing Succeeded status.*

Published the Restart-VM runbook. This script checks the VM's power state and starts it if stopped.

![Restart Runbook Published](./13-restart-runbook-published.png)
*Restart-VM runbook in Published state, ready to be triggered by alerts.*

Published the ScaleUp-VM runbook. This script checks the current VM size and upgrades it from Standard_D2s_v3 to Standard_D4s_v3 when CPU is consistently overloaded.

![ScaleUp Runbook Published](./14-scaleup-runbook-published.png)
*ScaleUp-VM runbook in Published state.*

Published the Cleanup-Disk runbook. This script runs remote cleanup commands on the VM to clear temp files and recover disk space.

![Cleanup Runbook Published](./15-cleanup-runbook-published.png)
*Cleanup-Disk runbook in Published state.*

Linked the runbooks to the alert rules through the action groups. When an alert fires, the action group triggers the correct runbook automatically.

![Alerts Linked to Runbooks](./16-alerts-linked-to-runbooks.png)
*Action group configuration showing the Automation Runbook action linked to the alert.*

### Phase 4 — Notification Pipeline

Created a Logic App to send email notifications when alerts fire and remediation actions complete. The Logic App uses an HTTP trigger and an Office 365 Outlook connector. It was added to the action group so it fires alongside the runbook automatically.

![Logic App Created](./17-logic-app-created.png)
*Logic App la-selfheal-notify created in East US.*

Configured the workflow in the Logic App designer. When triggered, it sends an email with the subject "Self-Healing Alert - Action Taken" and a message confirming that automated remediation was executed.

![Logic App Workflow](./18-logic-app-workflow.png)
*Logic App designer showing the HTTP trigger and email notification step.*

### Phase 5 — Testing

This is where the self-healing system proves itself. Instead of manually running the runbooks, I simulated real failures and let the system detect and fix them on its own.

**Test 1: VM Auto-Restart**

Stopped the VM using Stop-AzVM to simulate an unexpected shutdown.

![VM Stopped Manually](./19-vm-stopped-manually.png)
*VM showing deallocated state after being stopped from Cloud Shell.*

The Activity Log alert detected the deallocation and triggered the Restart-VM runbook through the action group. The runbook authenticated with managed identity, checked the VM state, and started it back up. The job completed successfully without any manual intervention.

![VM Auto-Restarted — Job Completed](./20-vm-auto-restarted.png)
*Automation job showing Completed status for the Restart-VM runbook.*

The runbook output confirms it detected the VM was stopped and initiated the auto-restart.

![Restart Runbook Output](./21-restart-runbook-output.png)
*Runbook output showing "VM was stopped. Auto-restart initiated."*

**Test 2: CPU Spike and Auto Scale-Up**

Created a second action group (ag-scaleup) with the ScaleUp-VM runbook attached and linked it to the CPU alert rule.

![CPU Alert Action Groups](./22-cpu-alert-action-groups.png)
*CPU alert rule showing the ScaleUp action group attached.*

Connected to the VM via RDP and ran PowerShell stress loops to push CPU to 100%.

![CPU Spike at 100%](./23-cpu-spike-detected.png)
*Task Manager inside the VM showing CPU at 100% utilization.*

After 5 minutes of sustained high CPU, the metric alert fired automatically.

![CPU Alert Fired](./24-cpu-alert-fired.png)
*Azure Monitor showing the CPU alert in fired state.*

The ScaleUp-VM runbook triggered automatically through the action group. It stopped the VM, changed the size from Standard_D2s_v3 to Standard_D4s_v3, and restarted it.

![ScaleUp Job Completed](./25-scaleup-job-completed.png)
*Automation job showing Completed status for the ScaleUp-VM runbook.*

Verified the VM was resized successfully.

![VM Scaled Up to D4s_v3](./26-vm-scaled-up.png)
*VM now running as Standard_D4s_v3 after automatic scale-up.*

**Job History and Email Confirmation**

Reviewed the full automation job history. All Restart-VM and ScaleUp-VM jobs show Completed status, confirming the self-healing system worked end to end.

![Automation Job History — All Completed](./27-automation-job-history.png)
*Full job history showing all runbook executions completed successfully.*

Configured the Logic App as an additional action in the action group so email notifications are sent alongside runbook execution.

![Action Group with Logic App](./28-action-group-with-logic-app.png)
*Action group showing both the Automation Runbook and Logic App actions configured.*

Received the email notification confirming that an alert was triggered and automated remediation was executed.

![Email Notification Received](./29-email-notification-received.png)
*Email received confirming self-healing action was taken on vm-workload.*

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
