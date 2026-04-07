Connect-AzAccount -Identity

$report = @()
$totalWaste = 0
$subId = (Get-AzContext).Subscription.Id
$token = (Get-AzAccessToken).Token
$headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }

# 1. Find orphaned managed disks
$disks = Get-AzDisk | Where-Object { $_.DiskState -eq "Unattached" }
foreach ($disk in $disks) {
    $monthlyCost = [math]::Round($disk.DiskSizeGB * 0.04, 2)
    $totalWaste += $monthlyCost
    $report += [PSCustomObject]@{
        ResourceType = "Orphaned Disk"
        ResourceName = $disk.Name
        ResourceGroup = $disk.ResourceGroupName
        Detail = "$($disk.DiskSizeGB) GB, $($disk.Sku.Name)"
        EstMonthlyCost = "$monthlyCost USD"
    }
}

# 2. Find unattached public IPs via REST API
try {
    $pipUrl = "https://management.azure.com/subscriptions/$subId/providers/Microsoft.Network/publicIPAddresses?api-version=2023-04-01"
    $pipResponse = Invoke-RestMethod -Uri $pipUrl -Headers $headers -Method Get
    foreach ($pip in $pipResponse.value) {
        if (-not $pip.properties.ipConfiguration) {
            $monthlyCost = 3.65
            $totalWaste += $monthlyCost
            $rgName = ($pip.id -split "/")[4]
            $report += [PSCustomObject]@{
                ResourceType = "Unattached Public IP"
                ResourceName = $pip.name
                ResourceGroup = $rgName
                Detail = "$($pip.properties.publicIPAllocationMethod), $($pip.properties.ipAddress)"
                EstMonthlyCost = "$monthlyCost USD"
            }
        }
    }
} catch {
    Write-Output "WARNING: Could not scan Public IPs - $($_.Exception.Message)"
}

# 3. Find orphaned NICs via REST API
try {
    $nicUrl = "https://management.azure.com/subscriptions/$subId/providers/Microsoft.Network/networkInterfaces?api-version=2023-04-01"
    $nicResponse = Invoke-RestMethod -Uri $nicUrl -Headers $headers -Method Get
    foreach ($nic in $nicResponse.value) {
        if (-not $nic.properties.virtualMachine) {
            $rgName = ($nic.id -split "/")[4]
            $report += [PSCustomObject]@{
                ResourceType = "Orphaned NIC"
                ResourceName = $nic.name
                ResourceGroup = $rgName
                Detail = "Not attached to any VM"
                EstMonthlyCost = "No direct cost"
            }
        }
    }
} catch {
    Write-Output "WARNING: Could not scan NICs - $($_.Exception.Message)"
}

# 4. Find unused NSGs via REST API
try {
    $nsgUrl = "https://management.azure.com/subscriptions/$subId/providers/Microsoft.Network/networkSecurityGroups?api-version=2023-04-01"
    $nsgResponse = Invoke-RestMethod -Uri $nsgUrl -Headers $headers -Method Get
    foreach ($nsg in $nsgResponse.value) {
        $hasNics = $nsg.properties.networkInterfaces.Count -gt 0
        $hasSubnets = $nsg.properties.subnets.Count -gt 0
        if (-not $hasNics -and -not $hasSubnets) {
            $rgName = ($nsg.id -split "/")[4]
            $report += [PSCustomObject]@{
                ResourceType = "Unused NSG"
                ResourceName = $nsg.name
                ResourceGroup = $rgName
                Detail = "Not associated with any subnet or NIC"
                EstMonthlyCost = "No direct cost"
            }
        }
    }
} catch {
    Write-Output "WARNING: Could not scan NSGs - $($_.Exception.Message)"
}

# 5. Find empty resource groups
$rgs = Get-AzResourceGroup
foreach ($rg in $rgs) {
    $resources = Get-AzResource -ResourceGroupName $rg.ResourceGroupName
    if ($resources.Count -eq 0) {
        $report += [PSCustomObject]@{
            ResourceType = "Empty Resource Group"
            ResourceName = $rg.ResourceGroupName
            ResourceGroup = $rg.ResourceGroupName
            Detail = "Contains zero resources"
            EstMonthlyCost = "No direct cost"
        }
    }
}

# Output report
Write-Output "============================================"
Write-Output "  CLOUD COST WATCHDOG - ZOMBIE RESOURCE SCAN"
Write-Output "  Scan Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm UTC')"
Write-Output "============================================"
Write-Output ""

if ($report.Count -eq 0) {
    Write-Output "No zombie resources found. Environment is clean."
} else {
    Write-Output "ZOMBIE RESOURCES DETECTED: $($report.Count)"
    Write-Output "ESTIMATED MONTHLY WASTE: $([math]::Round($totalWaste, 2)) USD"
    Write-Output ""
    Write-Output "--------------------------------------------"
    foreach ($item in $report) {
        Write-Output "Type:           $($item.ResourceType)"
        Write-Output "Name:           $($item.ResourceName)"
        Write-Output "Resource Group: $($item.ResourceGroup)"
        Write-Output "Detail:         $($item.Detail)"
        Write-Output "Est. Monthly:   $($item.EstMonthlyCost)"
        Write-Output "--------------------------------------------"
    }
    Write-Output ""
    Write-Output "RECOMMENDATION: Review and delete unused resources to reduce monthly spend."
}

# 6. Trigger Logic App email notification
$webhookUrl = "https://prod-14.eastus.logic.azure.com:443/workflows/dcd781b9a1a54693bdfcc7b143c5e6ae/triggers/When_an_HTTP_request_is_received/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2FWhen_an_HTTP_request_is_received%2Frun&sv=1.0&sig=IRhZWYlVazbWfwy49JMOYskg8KlrtgEZ_oWWWk18JVY"
try {
    $body = @{
        scanDate = (Get-Date -Format 'yyyy-MM-dd HH:mm UTC')
        zombieCount = $report.Count
        estimatedWaste = "$([math]::Round($totalWaste, 2)) USD"
    } | ConvertTo-Json
    Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json"
    Write-Output "Email notification triggered successfully."
} catch {
    Write-Output "WARNING: Could not trigger email notification - $($_.Exception.Message)"
}
