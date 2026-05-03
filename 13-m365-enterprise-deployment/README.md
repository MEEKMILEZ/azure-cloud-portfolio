# Microsoft 365 Enterprise Deployment for a Mid-Sized Organization

> End-to-end Microsoft 365 implementation for **TechSolutions Inc.** — a fictional 300-employee IT services firm — covering identity, security, compliance, collaboration, and operational monitoring on the **Microsoft 365 E5** plan. This is the kind of build-out a junior cloud admin or IT consultant inherits on day one of a real corporate rollout.

This is the natural follow-on from project 12 (small business setup): same product family, but the scope jumps to enterprise — premium licensing, Defender, Purview, DLP, Insider Risk, audit, and Power Automate-driven reporting.

---

## The Scenario

TechSolutions Inc. has 300 employees across three departments — IT, HR, and Marketing — and is moving from on-prem email and file shares to Microsoft 365. The IT team's brief:

> "Stand up the tenant, get everyone licensed and grouped properly, raise our Secure Score, encrypt internal mail, build out SharePoint sites with proper governance, lock down OneDrive, deploy Viva Engage as our internal social network, and turn on the auditing and reporting we need to satisfy the auditors."

Four workstreams cover that: **users & groups → security → collaboration → monitoring & reporting.**

---

## Glossary (plain-English version)

Before diving in, here's what the alphabet soup actually means:

- **E5 license** — the top-tier Microsoft 365 subscription. Includes everything (Office, email, SharePoint, Teams) plus the *premium* security and compliance tools (Defender for O365, Purview, Insider Risk Management). E3 is the mid-tier; E5 is "the works."
- **Microsoft Entra** — the new name for Azure Active Directory. The directory of users, groups, and permissions that every Microsoft cloud product checks against.
- **Microsoft 365 Group** — a team unit that automatically gets a shared mailbox, calendar, SharePoint site, and Teams channel. Add a person to the group → they get access to all of that in one shot.
- **Secure Score** — a 0–100% score Microsoft calculates for your tenant based on what security features you have turned on. Higher = harder to breach. Easy way to track security maturity over time.
- **Safe Links / Safe Attachments** — Defender features that scan URLs and attachments in real time before they reach the user. Safe Links rewrites links so they're checked when clicked; Safe Attachments runs files in a sandbox VM.
- **Mail flow rule (transport rule)** — Exchange's "if-this-then-that" for emails. Example: *"If the recipient is internal, encrypt the message."* Rules run on every message that flows through the tenant.
- **Microsoft 365 Message Encryption / RMS** — encrypts emails so only the intended recipient can read them. Works even if the email is forwarded.
- **DLP (Data Loss Prevention)** — automated scanning of documents/emails/chat for sensitive data (credit card numbers, bank accounts, SINs). When found, DLP can block sharing or alert admins.
- **Insider Risk Management** — Purview feature that watches employee behaviour for risky patterns (mass downloads, mass deletions, suspicious sharing) — like a smoke detector for data leaks.
- **Audit log** — append-only record of every administrative and user action in the tenant. Critical for forensics and compliance.
- **Microsoft Purview** — Microsoft's umbrella name for data governance, compliance, retention, DLP, and Insider Risk.
- **Viva Engage** — Microsoft's enterprise social network (formerly Yammer). Like an internal LinkedIn/Twitter for the company.
- **Power Automate** — Microsoft's no-code automation platform. Build "when X happens, do Y" workflows without writing software.
- **Service Health** — Microsoft's status dashboard showing whether each M365 service is up, degraded, or down.

---

## Workstream 1 — Users, Groups, and Permissions

The foundation. Every other Microsoft 365 service (mail, files, chat, meetings) hangs off the user directory.

### 1.1 Bulk-import 10 users from CSV

Used the M365 admin center's **bulk import** feature to create 10 users at once from a CSV file. Doing this from a spreadsheet is how real companies onboard cohorts — much faster than clicking *Add user* ten times, and the same CSV format scales to hundreds.

![Bulk-importing 10 users from a CSV file in the M365 admin center](images/01-bulk-import-users-csv.png)

### 1.2 Assign Microsoft 365 E5 licenses

Attached the **Microsoft 365 E5** license to all 10 imported users. E5 unlocks the premium security and compliance features (Defender for Office 365, Purview Insider Risk, advanced eDiscovery) that the rest of the project needs.

![All 10 users assigned Microsoft 365 E5 licenses](images/02-assign-e5-licenses.png)

### 1.3 Configure user profiles

Filled out each user with a profile picture, contact info, and job title. These details flow through to Outlook, Teams, SharePoint search, and the org chart — they're how staff find each other.

![User profile basic information](images/03-user-profile-basic-info.png)
![User profile contact details](images/04-user-profile-contact-details.png)

### 1.4 Add organisation-specific user information

Set department, manager, employee ID, office location, and hire date for each user in **Microsoft Entra**. This metadata feeds dynamic groups, conditional access policies, and HR reporting.

![Organisational info for Maria Williams (Systems Administrator, IT)](images/05-user-org-info-maria-williams.png)
![Organisational info for Sarah Davis (HR Director)](images/06-user-org-info-sarah-davis.png)
![Continued profile setup for Sarah Davis](images/07-user-org-info-sarah-davis-detail.png)
![Profile setup for Daniel Garcia (Marketing Director)](images/08-user-org-info-daniel-garcia.png)

### 1.5 Create three Microsoft 365 Groups

Created one group per department — **IT**, **Human Resources**, and **Marketing**. Each group automatically gets its own shared mailbox, calendar, SharePoint site, and Teams channel — the entire collaboration kit, provisioned in one click per group.

![Three departmental Microsoft 365 Groups created](images/09-create-departmental-groups.png)

### 1.6 Add users to their respective groups

Group membership is what controls access. Members of HR get HR's mailbox, files, and Teams channel — nobody outside HR does.

![HR group membership: Amanda Wilson, Kevin Miller, Sarah Davis](images/10-add-members-hr-group.png)
![IT group membership: John Smith, Maria Williams, Robert Johnson](images/11-add-members-it-group.png)
![Marketing group with Daniel Garcia as Owner](images/12-add-members-marketing-group.png)

### 1.7 Configure department-specific permissions

HR documents are sensitive (payroll, performance reviews) — granted **Edit** permission on the HR SharePoint site to HR members only, leaving everyone else without even Read access.

![HR members granted Edit permissions on the HR SharePoint site](images/13-hr-sharepoint-edit-permissions.png)

The Marketing team needs to spin up campaign-specific Teams quickly, so confirmed members have **Owner/Member** rights in Teams to create channels and manage content.

![Marketing Teams permissions confirmed: Daniel as Owner, others as Members](images/14-marketing-teams-permissions.png)

---

## Workstream 2 — Security and Encryption

E5 unlocks Microsoft's enterprise security stack — **Microsoft Defender for Office 365** and **Microsoft Purview**. This workstream gets the most important pieces switched on.

### 2.1 Establish a Secure Score baseline

Pulled up the **Microsoft Secure Score** dashboard to capture TechSolutions' starting posture: **43.33%**. Secure Score is Microsoft's gamified summary of your security configuration — every recommended action that gets checked off raises the score. Logging the baseline now makes "before/after" reporting easy as the rest of the project rolls out.

![Microsoft Secure Score baseline of 43.33%](images/15-defender-secure-score-baseline.png)

### 2.2 Enable Safe Links and Safe Attachments

Turned on **Safe Links** (rewrites every URL so it's scanned at click-time) and **Safe Attachments** (detonates suspicious files in a sandbox VM before delivery) for all users via Defender's *standard protection* preset. This is the single most impactful setting for stopping phishing and malware in their tracks.

![Safe Links and Safe Attachments enabled organisation-wide](images/16-safe-links-attachments-enabled.png)

### 2.3 Configure anti-phishing / anti-spam / anti-malware policy

Reviewed and tuned the standard Defender policy that scans inbound mail for phishing, spam, malware, and impersonation attacks. Spoofing thresholds are set tight enough to catch attackers pretending to be the CEO without false-flagging legit business email.

![Anti-phishing, anti-malware, and anti-spam policy configured](images/17-anti-phishing-malware-spam-policy.png)

### 2.4 Set up Microsoft 365 Message Encryption

Configured **Microsoft 365 Message Encryption (MSME)** so messages can be encrypted on demand and remain protected even when forwarded outside the company.

![Microsoft 365 Message Encryption configured](images/18-message-encryption-configured.png)

### 2.5 Auto-encrypt all internal email

Built an Exchange **mail flow rule** called *"Encrypt all internal email — TechSolutions"* that automatically applies the **Confidential \ All Employees** RMS template to every message sent between employees. End result: an outsider who somehow intercepts internal mail sees gibberish, not plain text.

![Mail flow rule auto-encrypting all internal email](images/19-internal-email-encryption-rule.png)

---

## Workstream 3 — Collaboration: SharePoint, OneDrive, Viva Engage

Where work actually happens.

### 3.1 Create three departmental SharePoint sites

One **SharePoint Online** site per department — IT, HR, and Marketing — each populated with the right group members. These sites become the home for departmental files, news, and pages.

![IT department SharePoint site](images/20-sharepoint-it-site.png)
![HR department SharePoint site](images/21-sharepoint-hr-site.png)
![Marketing department SharePoint site](images/22-sharepoint-marketing-site.png)

### 3.2 Configure document libraries and per-site permissions

Each site gets its own document library with appropriate **permission levels** — department members get *Edit*, the Global Admin keeps *Owner*, nobody else has access.

![IT document library and permissions](images/23-it-document-library-permissions.png)
![HR document library and permissions](images/24-hr-document-library-permissions.png)
![Marketing document library and permissions](images/25-marketing-document-library-permissions.png)

### 3.3 Enable versioning and content approval on the HR library

HR docs get the strictest controls. Turned on **versioning** (keeps the last 100 major and minor versions of every file — so you can roll back) and **content approval** (a doc isn't visible to others until an HR approver signs off). This is governance you can show an auditor.

![HR library: versioning + content approval enabled](images/26-hr-versioning-content-approval.png)

### 3.4 Restrict OneDrive external sharing

Set the OneDrive sharing policy at the org level to **Internal only** — no anonymous links, no external-guest sharing. The single most important data-leak control in any tenant.

![OneDrive external sharing restricted](images/27-onedrive-external-sharing-restricted.png)

### 3.5 Five-year retention policy for business files

Created a **Microsoft Purview retention policy** that retains business-critical OneDrive files for **5 years**, satisfying typical record-keeping requirements. Even if a user deletes a file, Purview keeps a hidden copy for the retention window.

![Five-year retention policy in Microsoft Purview](images/28-purview-five-year-retention-policy.png)

### 3.6 Auto-cleanup files older than one year

Built a **Power Automate** flow that runs monthly, scans OneDrive for files older than 1 year, and moves them to the Recycle Bin. Keeps the active dataset clean while the 5-year retention policy keeps a recoverable copy in the background.

![Power Automate flow for old-file cleanup](images/29-power-automate-old-files-cleanup.png)

### 3.7 Configure Viva Engage for internal-only use

Turned on **Viva Engage** (Microsoft's enterprise social network — think internal LinkedIn) and locked it to **internal communications only** — external networks are off, only `@techsolutions.com` accounts can post.

![Viva Engage usage policy](images/30-viva-engage-usage-policy.png)
![Viva Engage policy guidelines](images/31-viva-engage-policy-guidelines.png)

### 3.8 Create company-wide and departmental Viva communities

Spun up four communities: **Company-wide Announcements** (broadcast channel for the whole company) plus three departmental discussion spaces.

![Company-wide Announcements community](images/32-viva-company-announcements-community.png)
![IT discussion community](images/33-viva-it-discussion-community.png)
![HR discussion community](images/34-viva-hr-discussion-community.png)
![Marketing discussion community](images/35-viva-marketing-discussion-community.png)

### 3.9 Pin the social media policy to the home feed

Pinned a permanent policy reminder to the Viva Engage home feed so every user sees TechSolutions' social media guidelines on every visit. Compliance through visibility.

![Social media policy reminder pinned to Viva Engage feed](images/36-viva-policy-reminder-feed.png)

---

## Workstream 4 — Monitoring, Governance, and Reporting

You can't manage what you can't see. This workstream turns on the dashboards, alerts, and reports that let IT actually run the environment.

### 4.1 Enable audit logging and a custom search

Switched on **audit logging** in the Microsoft 365 Compliance Center (it's not on by default in some plans) so every admin and user action — sign-ins, file downloads, permission changes, group adds — is recorded. Created a saved search called **TechSolutions SharePoint Updates** that pulls all SharePoint file modifications across the tenant.

![Audit logging enabled and custom search created](images/37-audit-log-enabled-search-created.png)

### 4.2 Run the audit log search

The saved search returns a clean event-by-event view of who edited what, when, and from where. Critical for incident response and audits.

![Audit log results showing SharePoint file modifications](images/38-audit-log-sharepoint-results.png)

### 4.3 Alert on mass file deletion

Configured a **Defender alert policy** with **High** severity that pages an admin the moment someone deletes an unusual number of files in a short window — the classic ransomware or disgruntled-leaver pattern.

![Mass file deletion alert policy](images/39-mass-deletion-alert-policy.png)

### 4.4 Build a DLP policy for financial data

Created a **Data Loss Prevention** policy named **TechSolutions Financial Data Protection** that scans every M365 location (Exchange, SharePoint, OneDrive, Teams, Endpoint) for credit card numbers, bank account numbers, and other financial identifiers. Users get a **policy tip** ("you're about to share something sensitive") and admins get an incident report when the policy fires.

![DLP policy: locations and conditions](images/40-dlp-financial-data-policy-config.png)
![DLP policy: rules and actions](images/41-dlp-financial-data-policy-rules.png)

### 4.5 Insider Risk Management policy

**Insider Risk Management** (Purview feature) watches for the *behavioural* signals of data theft — printing/downloading at unusual times, exfiltrating to personal cloud, sharing externally — and surfaces a risk score for each user. Configured a policy that monitors SharePoint, email, and Teams.

![Insider Risk policy review](images/42-insider-risk-policy-review.png)
![Insider Risk policy created and live](images/43-insider-risk-policy-created.png)

### 4.6 Generate usage reports

Pulled the built-in **Email activity** and **SharePoint usage** reports for the last 30 days — sent/received/read counts, file activity, page visits. These reports are how IT proves to leadership that the platform is being used (and where adoption gaps live).

![Exchange email activity report](images/44-exchange-email-activity-report.png)
![SharePoint usage report](images/45-sharepoint-usage-report.png)

### 4.7 Schedule monthly reports via Power Automate

Created a **distribution list** for IT admins, then built a **Power Automate** flow that fires on the 1st of every month, generates a usage summary, and emails the link to the distribution list. No more manually running reports each month.

![IT admins distribution list](images/46-it-admins-distribution-list.png)
![Power Automate flow for monthly report delivery](images/47-power-automate-monthly-report-flow.png)

### 4.8 Service Health alerts and dashboard

Configured **Service Health** alerts so the primary admin AND the IT team distribution list both get notified the moment Microsoft posts an incident affecting any M365 service. Then bookmarked the Service Health dashboard for at-a-glance status checks.

![Service Health alert configuration](images/48-service-health-alert-config.png)
![Service Health dashboard](images/49-service-health-dashboard.png)

---

## What's Now Running

After the four workstreams, TechSolutions Inc. has gone from "fresh tenant" to "enterprise-ready":

- **Identity & licensing:** 10 E5-licensed users across IT, HR, Marketing, with profiles, manager hierarchies, and groups
- **Security baseline:** Defender for Office 365 with Safe Links, Safe Attachments, anti-phishing, internal email encryption
- **Governance:** Per-department SharePoint sites with proper permissions, content approval on HR, OneDrive external sharing locked off
- **Compliance:** 5-year retention, financial-data DLP, Insider Risk Management
- **Operations:** Audit logging, mass-deletion alerts, monthly usage reporting via Power Automate, Service Health notifications

---

## What I'd Do Next

Logical follow-on work, deliberately out of scope here:

- **Conditional Access** — require MFA from untrusted networks, block legacy authentication, restrict access to corporate devices
- **Defender for Endpoint** — extend protection from email to laptops/desktops
- **Sensitivity labels** — let users label docs *Confidential / Public / Internal* and have those labels drive encryption and DLP
- **Intune device management** — enrol all corporate Windows and mobile devices, push compliance baselines
- **Shadow IT discovery** with Defender for Cloud Apps to find unsanctioned SaaS in use
- **Tabletop exercise** — run a phishing simulation through Defender's Attack Simulation Training and measure click rates

---

## Tech Stack

- Microsoft 365 E5
- Microsoft Entra (formerly Azure AD)
- Microsoft Defender for Office 365 (Safe Links, Safe Attachments, anti-phishing, alert policies)
- Microsoft Purview (retention, DLP, Insider Risk Management, audit log)
- Exchange Online (transport rules, message encryption, distribution lists)
- SharePoint Online and OneDrive for Business
- Microsoft Teams
- Viva Engage (formerly Yammer)
- Power Automate
