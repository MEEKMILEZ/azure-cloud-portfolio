# Azure Cloud Portfolio

Hands-on cloud infrastructure projects built in Microsoft Azure. Each project solves a real-world problem using production-grade services, deployed via Azure Cloud Shell and Terraform, and documented with architecture diagrams, screenshots, and troubleshooting notes.

## Certifications

- MS-900: Microsoft 365 Fundamentals -- Certified
- AZ-900: Azure Fundamentals -- Certified
- AZ-104: Azure Administrator Associate -- In Progress
- AWS Cloud Practitioner -- In Progress

## Projects

| # | Project | What It Does | Technologies |
|---|---------|-------------|--------------|
| 01 | [Azure VM Deployment](./01-azure-vm-deployment) | Deployed and configured Windows VMs with networking, NSGs, and remote access | Azure VMs, VNets, NSGs, Bastion, PowerShell |
| 02 | [Hub-Spoke Network](./02-hub-spoke-network) | Built a hub-spoke network topology with VNet peering, Bastion, and segmented subnets | VNet Peering, Bastion, NSGs, Route Tables |
| 03 | [Azure Firewall](./03-azure-firewall) | Configured Azure Firewall with application and network rules for centralized traffic control | Azure Firewall, UDRs, NAT Rules, Threat Intelligence |
| 04 | [Service Endpoints and Storage](./04-service-endpoints-storage) | Secured storage account access using service endpoints and VNet rules | Service Endpoints, Storage Accounts, VNet Rules |
| 05 | [Azure Security Monitoring and Microsoft Sentinel SIEM](./05-azure-security-monitoring) | Deployed Microsoft Sentinel with automated incident response and threat detection | Microsoft Sentinel, Defender for Cloud, Logic Apps, JIT VM Access |
| 06 | [Automated Backup Verification and Reporting](./06-automated-backup-verification) | Built automated backup monitoring that scans all vaults daily and emails a status report | Azure Automation, Recovery Services Vault, Logic Apps, Managed Identity, REST API |
| 07 | [Self-Healing Infrastructure with IaC](./07-self-healing-infrastructure) | Deployed entire environment from Bicep, with automated monitoring, self-healing runbooks, and email notifications | Azure Bicep, Automation Runbooks, Azure Monitor, Logic Apps, Managed Identity |
| 08 | [Cloud Cost Watchdog](./08-cloud-cost-watchdog) | Automated zombie resource detection and cost optimization across the entire subscription | Terraform, Azure Automation, REST API, Logic Apps, Managed Identity, FinOps |
| 12 | [Microsoft 365 Tenant Deployment](./12-m365-tenant-deployment) | End-to-end M365 build-out for a small business — branding, identity, Exchange, SharePoint/OneDrive, anti-malware | M365 Admin Center, Exchange, SharePoint, OneDrive, Microsoft Graph PowerShell, Microsoft Defender |
| 13 | [Microsoft 365 Enterprise Deployment](./13-m365-enterprise-deployment) | Enterprise M365 rollout for a 300-employee mid-sized company — bulk user onboarding, E5 security baseline, Purview compliance, DLP, Insider Risk, audit, Power Automate reporting | M365 E5, Microsoft Entra, Defender for Office 365, Microsoft Purview, Exchange Online, SharePoint, OneDrive, Viva Engage, Power Automate |

## About

Built by Paschal Nnenna. Cloud Administrator based in Toronto with hands-on experience in Azure infrastructure, automation, security, monitoring, and cost optimization.

- LinkedIn: [linkedin.com/in/paschal-nnenna](https://linkedin.com/in/paschal-nnenna)
- GitHub: [github.com/MEEKMILEZ](https://github.com/MEEKMILEZ)
