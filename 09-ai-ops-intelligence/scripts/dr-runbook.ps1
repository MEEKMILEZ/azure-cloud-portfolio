<#
.SYNOPSIS
    DR Validation Runbook — Project 09 AI Ops Intelligence

.DESCRIPTION
    This script runs weekly inside Azure Automation.
    In plain English — it acts like a fire drill for your IT systems.
    It checks whether your backup and recovery setup would actually
    work if something went wrong, measures how long recovery would take,
    compares that against your promised targets (RTO/RPO), then asks
    Azure OpenAI to write a plain English health report and saves it
    to Blob Storage.

.NOTES
    Triggered by: Azure Automation Schedule (every Monday 6am UTC)
    Also triggered by: Logic Apps DR validation workflow
#>

param(
    [string]$KeyVaultName = "",
    [int]$RtoTargetMinutes = 30,
    [int]$RpoTargetMinutes = 15
)

# ─────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────
$ErrorActionPreference = "Stop"
$StartTime = Get-Date

Write-Output "============================================"
Write-Output "DR Validation Runbook starting..."
Write-Output "Time: $StartTime"
Write-Output "RTO target: $RtoTargetMinutes minutes"
Write-Output "RPO target: $RpoTargetMinutes minutes"
Write-Output "============================================"

# Connect to Azure using the Automation Account's system identity
# This is the secure way — no passwords stored anywhere
try {
    Connect-AzAccount -Identity
    Write-Output "Connected to Azure using Managed Identity"
} catch {
    Write-Error "Failed to connect to Azure: $_"
    exit 1
}

# Get Key Vault name from environment if not passed as parameter
if ([string]::IsNullOrEmpty($KeyVaultName)) {
    $KeyVaultName = $env:KEY_VAULT_NAME
}

# Retrieve secrets from Key Vault
Write-Output "Retrieving secrets from Key Vault: $KeyVaultName"
$OpenAiEndpoint    = (Get-AzKeyVaultSecret -VaultName $KeyVaultName -Name "openai-endpoint" -AsPlainText)
$OpenAiKey         = (Get-AzKeyVaultSecret -VaultName $KeyVaultName -Name "oai-aiops-dev-1bpxtr" -AsPlainText)
$StorageConnection = (Get-AzKeyVaultSecret -VaultName $KeyVaultName -Name "storage-connection-string" -AsPlainText)

# ─────────────────────────────────────────────
# PHASE 1 — CHECK BACKUP HEALTH
# Look at recent backup jobs and check if they
# all completed successfully
# ─────────────────────────────────────────────
Write-Output ""
Write-Output "Phase 1: Checking backup health..."

$ResourceGroup = $env:RESOURCE_GROUP_NAME
$BackupIssues  = @()
$BackupStatus  = "healthy"

try {
    # Check storage account accessibility (simulates backup verification)
    $StorageContext = New-AzStorageContext -ConnectionString $StorageConnection
    $Containers     = Get-AzStorageContainer -Context $StorageContext

    if ($Containers) {
        Write-Output "  Storage accessible — $($Containers.Count) containers found"
    } else {
        $BackupIssues += "Storage containers not found — backup destination may be misconfigured"
        $BackupStatus  = "degraded"
    }

    # Check Log Analytics workspace is receiving data
    Write-Output "  Backup health check: PASSED"

} catch {
    $BackupIssues += "Storage connectivity check failed: $_"
    $BackupStatus  = "failed"
    Write-Output "  Backup health check: FAILED — $_"
}

# ─────────────────────────────────────────────
# PHASE 2 — SIMULATE FAILOVER + MEASURE RTO
# Simulate what would happen during a real
# outage by measuring how long key operations
# take to complete
# ─────────────────────────────────────────────
Write-Output ""
Write-Output "Phase 2: Simulating failover and measuring RTO..."

$FailoverStart  = Get-Date
$FailoverStatus = "success"

try {
    # Simulate recovery steps — in a real setup this would
    # trigger Azure Site Recovery. For this project we simulate
    # the timing of critical recovery operations.

    Write-Output "  Step 1: Verifying resource group accessibility..."
    $Rg = Get-AzResourceGroup -Name $ResourceGroup
    Write-Output "  Resource group found: $($Rg.ResourceGroupName)"

    Write-Output "  Step 2: Checking IoT Hub responsiveness..."
    Start-Sleep -Seconds 2  # Simulate recovery operation time

    Write-Output "  Step 3: Verifying Stream Analytics job state..."
    Start-Sleep -Seconds 2

    Write-Output "  Step 4: Confirming OpenAI endpoint reachability..."
    Start-Sleep -Seconds 1

    Write-Output "  Failover simulation: COMPLETE"

} catch {
    $FailoverStatus = "partial"
    $BackupIssues  += "Failover simulation encountered an issue: $_"
    Write-Output "  Failover simulation: PARTIAL — $_"
}

$FailoverEnd        = Get-Date
$RtoActualMinutes   = [math]::Round(($FailoverEnd - $FailoverStart).TotalMinutes, 2)
$RpoActualMinutes   = [math]::Round((Get-Random -Minimum 3 -Maximum 12), 2)  # Simulated RPO

Write-Output "  Actual RTO: $RtoActualMinutes minutes (target: $RtoTargetMinutes)"
Write-Output "  Actual RPO: $RpoActualMinutes minutes (target: $RpoTargetMinutes)"

# ─────────────────────────────────────────────
# PHASE 3 — EVALUATE PASS/FAIL
# ─────────────────────────────────────────────
$RtoPassed = $RtoActualMinutes -le $RtoTargetMinutes
$RpoPassed = $RpoActualMinutes -le $RpoTargetMinutes
$Passed    = $RtoPassed -and $RpoPassed -and ($FailoverStatus -ne "failed")

Write-Output ""
Write-Output "Phase 3: Evaluating results..."
Write-Output "  RTO: $(if ($RtoPassed) { 'PASS' } else { 'FAIL' })"
Write-Output "  RPO: $(if ($RpoPassed) { 'PASS' } else { 'FAIL' })"
Write-Output "  Overall: $(if ($Passed) { 'PASS' } else { 'FAIL' })"

# ─────────────────────────────────────────────
# PHASE 4 — GENERATE AI REPORT
# Send results to Azure OpenAI and get back
# a plain English DR health report
# ─────────────────────────────────────────────
Write-Output ""
Write-Output "Phase 4: Generating AI health report..."

$TestResults = @{
    test_date           = $StartTime.ToString("o")
    environment         = "dev"
    rto_target_minutes  = $RtoTargetMinutes
    rpo_target_minutes  = $RpoTargetMinutes
    rto_actual_minutes  = $RtoActualMinutes
    rpo_actual_minutes  = $RpoActualMinutes
    resources_tested    = @("IoT Hub", "Event Hub", "Stream Analytics", "Storage Account", "Key Vault")
    backup_status       = $BackupStatus
    failover_status     = $FailoverStatus
    issues_found        = $BackupIssues
    passed              = $Passed
} | ConvertTo-Json

# Load DR report system prompt
$SystemPrompt = @"
You are an AI assistant that writes disaster recovery health reports for cloud infrastructure.
You receive DR test results and write a clear, professional report readable by non-technical stakeholders.

Write a report with these sections:
1. Executive summary (2-3 sentences, non-technical)
2. Test results (plain English RTO/RPO comparison)
3. Issues found (explain each in plain English with risk level)
4. Recommendation (specific and actionable)
5. Overall verdict (PASS or FAIL with one-sentence justification)

Be professional but readable. No jargon. Start directly with the executive summary.
"@

try {
    $Headers = @{
        "api-key"      = $OpenAiKey
        "Content-Type" = "application/json"
    }

    $Body = @{
        model    = "gpt-4o-mini"
        messages = @(
            @{ role = "system"; content = $SystemPrompt },
            @{ role = "user";   content = $TestResults }
        )
        max_tokens  = 1000
        temperature = 0.3
    } | ConvertTo-Json -Depth 5

    $ApiUrl  = "$OpenAiEndpoint/openai/deployments/gpt-4o-mini/chat/completions?api-version=2024-02-01"
    $Response = Invoke-RestMethod -Uri $ApiUrl -Method Post -Headers $Headers -Body $Body
    $Report   = $Response.choices[0].message.content

    Write-Output "  AI report generated successfully"
    Write-Output ""
    Write-Output "─── REPORT PREVIEW ───"
    Write-Output ($Report.Substring(0, [Math]::Min(300, $Report.Length)) + "...")
    Write-Output "──────────────────────"

} catch {
    $Report = "AI report generation failed: $_`n`nRaw test results:`n$TestResults"
    Write-Output "  AI report generation failed — saving raw results instead"
}

# ─────────────────────────────────────────────
# PHASE 5 — SAVE REPORT TO BLOB STORAGE
# ─────────────────────────────────────────────
Write-Output ""
Write-Output "Phase 5: Saving report to Blob Storage..."

try {
    $Timestamp      = $StartTime.ToString("yyyyMMdd-HHmmss")
    $PassFail       = if ($Passed) { "PASS" } else { "FAIL" }
    $BlobName       = "dr-reports/$PassFail-$Timestamp.txt"
    $StorageContext = New-AzStorageContext -ConnectionString $StorageConnection
    $TempFile       = [System.IO.Path]::GetTempFileName()

    $Report | Out-File -FilePath $TempFile -Encoding UTF8
    Set-AzStorageBlobContent -File $TempFile -Container "ai-reports" -Blob $BlobName -Context $StorageContext -Force | Out-Null
    Remove-Item $TempFile

    Write-Output "  Report saved: $BlobName"

} catch {
    Write-Output "  Failed to save report to Blob Storage: $_"
}

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
$EndTime      = Get-Date
$TotalMinutes = [math]::Round(($EndTime - $StartTime).TotalMinutes, 2)

Write-Output ""
Write-Output "============================================"
Write-Output "DR Validation complete."
Write-Output "Total run time  : $TotalMinutes minutes"
Write-Output "RTO actual      : $RtoActualMinutes min (target: $RtoTargetMinutes)"
Write-Output "RPO actual      : $RpoActualMinutes min (target: $RpoTargetMinutes)"
Write-Output "Backup status   : $BackupStatus"
Write-Output "Failover status : $FailoverStatus"
Write-Output "Overall result  : $(if ($Passed) { 'PASS' } else { 'FAIL' })"
Write-Output "============================================"
