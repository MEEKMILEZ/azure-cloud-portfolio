# Project 12: Microsoft 365 Tenant Deployment for a Small Business

## The Scenario

Dr. Sarah Park is opening a four physician family medicine clinic in Mississauga. She has hired three nurses, two front desk staff, and an office manager. The clinic opens in three weeks. There is no IT department. Patient intake forms are still on a paper stack at the empty front desk.

Her cousin, who runs an accounting firm, tells her she needs Microsoft 365 Business Standard for proper email, shared documents, and a paper trail that satisfies PHIPA. Sarah does not know what any of those words mean. She has a tenant signup confirmation in her inbox and ten days before patients walk through the door.

She emails me on a Sunday night.

This README is what I delivered. It is also the kind of work small healthcare clinics, dental offices, physiotherapy practices, and law firms across the GTA pay an MSP or independent IT consultant to deliver in their first week of opening.

## Why This Matters

Mississauga has more than 200 small medical clinics: family medicine, dental, physiotherapy, walk in, optometry, and specialty practices. Across the GTA, the number runs into the thousands. Most of them are running on a setup that looks like this:

- Personal Outlook.com or Gmail accounts shared between staff
- Patient files on a USB drive in a desk drawer
- Documents emailed back and forth as attachments
- No central admin, no audit trail, no MFA
- One ransomware incident away from a regulatory disaster

The compliance reality:

| Item | Real value |
|---|---|
| PHIPA fine ceiling for an individual provider | 200,000 CAD |
| PHIPA fine ceiling for a corporation | 1,000,000 CAD |
| HIPAA fine ceiling for "willful neglect" | 1.5M USD per violation type per year |
| Microsoft 365 Business Standard cost | ~16.20 CAD per user per month |
| 8 person clinic monthly M365 cost | ~130 CAD per month |
| Average MSP rate for healthcare IT | 75 to 150 USD per user per month |

Microsoft 365 done right is the cheapest insurance policy a small healthcare practice will ever buy. The problem is that "done right" is not what you get out of the box. A fresh tenant has anonymous OneDrive sharing turned on, no MFA enforcement, no anti malware tuning, no branding, and no audit configuration. Someone has to actually build it.

This project is that build, end to end, for an 8 person clinic. Same playbook applies to the dental office next door, the physio clinic across the street, or a four lawyer firm in Burlington.

## What I Built

Five workstreams that take a fresh M365 tenant from signup to "Sarah's clinic can open Monday morning."

The brief from Sarah:

> "Make it look like ours. Get Katy and Mike on it as the pilot users so I can test before bringing on the rest. Set up our `info@` shared inbox and the `team@` distribution list so patient bookings come to the right people. Lock down our anti malware and file sharing so nothing leaks. Give us a SharePoint site for staff training documents. And do not leave anything on defaults that an auditor would write up."

That brief breaks into five workstreams: brand the tenant, set up identity and licensing, install and test the apps, configure email infrastructure and protection, and stand up SharePoint and OneDrive.

## Glossary (plain English)

A few words that come up a lot in this project, explained in normal language:

- **Tenant** is your organisation's own private space inside Microsoft 365. Two different companies on M365 each have their own tenant; they cannot see each other's data.
- **Microsoft 365 Admin Center** is the main website (admin.cloud.microsoft) where the IT admin manages everything.
- **PowerShell** is Microsoft's command line tool. Instead of clicking buttons in a web page, you type instructions and it does them. Faster for repetitive jobs (like creating 50 users at once).
- **License** is a "seat" you have paid Microsoft for. A license decides which M365 apps a user can use (Word, Outlook, Teams, etc.). No license means the user can sign in but cannot actually use anything.
- **Exchange** is the part of M365 that handles email. The Exchange Admin Center is where you manage mailboxes, distribution lists, anti spam, etc.
- **Shared mailbox** is one inbox that several people can read and reply from (e.g., `info@meekcloud.com`). Cheaper than giving each support agent their own license.
- **Distribution list** is an email address that fans out to a group of people. Email `team@meekcloud.com` once, everyone on the list gets it.
- **SharePoint** is Microsoft's website and document library platform. Internal team sites, company intranet pages, document storage with permissions.
- **OneDrive** is personal cloud file storage that comes with each user's M365 license. Like Dropbox, but built into Windows.
- **Anti malware policy** is the rules Microsoft Defender uses to scan incoming email for viruses and decide what to do with bad attachments.
- **PHIPA** is Ontario's Personal Health Information Protection Act. The law that says clinics like Sarah's have to keep patient data private and have an audit trail.

## Workstream 1: Brand the Tenant

A fresh M365 tenant looks the same as everyone else's. The first job is to make it feel like the clinic's own environment so staff trust what they are logging into. Branding is also the cheapest social engineering defense a small business has: a phishing email that looks like Microsoft's generic sign in page is more believable to a user who has never seen the clinic's actual portal.

### 1.1 Upload the company logo

The custom logo now appears in the top left of the Microsoft 365 admin center and on staff sign in pages. Front desk staff signing in for the first time see the clinic's logo, not a generic Microsoft purple banner.

![Tenant logo uploaded and visible in the admin center](images/01-tenant-logo-uploaded.png)

### 1.2 Apply a custom color theme

Switched the admin center's accent colour and header to match the clinic's brand palette. Small touch, but it tells employees they are inside the right place.

![Custom color theme applied across the admin center](images/02-color-theme-customized.png)

### 1.3 Make the logo clickable

Configured the logo so that clicking it opens the clinic's website. Useful for jumping back to public facing resources from inside the admin portal.

![Logo configured to open the company URL when clicked](images/03-logo-link-configured.png)

### 1.4 Add helpdesk contact info

If a user runs into trouble (a forgotten password the morning of a busy clinic day), the M365 portal now shows them how to reach internal IT support: phone, email, and helpdesk URL. For Sarah's clinic this initially points at me as the consultant; in the long term it would point at whatever MSP takes over support.

![Helpdesk contact information set in the organization profile](images/04-helpdesk-contact-set.png)

### 1.5 Pick early release pilot users

Selected two users (Katy and James) to receive Microsoft feature updates before they roll out to the wider organisation. This is a "release ring", a small controlled group that catches breaking changes before they hit the rest of the staff. In a clinic context, you do not want a Microsoft Outlook update breaking calendar invites the morning of a fully booked Monday.

![Two users selected for early Microsoft feature releases](images/05-early-release-users-selected.png)

## Workstream 2: Identity and Licensing via PowerShell

Clicking through the admin UI is fine for one or two users. But real environments use PowerShell because it is repeatable and auditable. You can save the script and run it again next month when the clinic hires its fifth nurse, or hand it to the next IT consultant who picks up the contract.

### 2.1 Install the Microsoft Graph PowerShell module and connect

Installed the **Microsoft.Graph** PowerShell module on the admin workstation, then ran `Connect-MgGraph` with the right scopes (permission flags). After signing in once, every subsequent command runs against the live tenant.

![Installing the Microsoft Graph PowerShell module](images/06-powershell-module-install.png)
![Connected to Microsoft 365 with Connect-MgGraph](images/07-powershell-connect-to-m365.png)

### 2.2 Create the two pilot users

Used `New-MgUser` to provision Katy and James as the pilot user accounts. Doing it in PowerShell means the same script can be reused later to bulk create the rest of the staff from a CSV the office manager exports from the HR system.

![First pilot user (Katy Price) created via PowerShell](images/08-powershell-create-user-katy.png)
![Second pilot user created via PowerShell](images/09-powershell-create-user-second.png)

### 2.3 Assign licenses

A user without a license is just a name in the directory. They cannot open Outlook or Word, and any patient data they touch is not actually inside the protected tenant. Used `Set-MgUserLicense` to attach a Microsoft 365 trial license to each pilot account. In production this would be Microsoft 365 Business Standard at 16.20 CAD per user per month.

![Microsoft 365 license assigned to the pilot users with PowerShell](images/10-powershell-assign-license.png)

## Workstream 3: Install and Test Microsoft 365 Apps

Provisioning users is meaningless until someone actually uses them. This workstream proves the licenses work end to end.

### 3.1 Install Office on a Windows VM

Installed the full Microsoft 365 Apps for enterprise package on a Windows virtual machine and signed in with the first pilot user to activate the install (Office contacts Microsoft to confirm there is a license tied to the account). The VM stands in for the desktop computer at the front desk.

![Office installed and activated on the test VM](images/11-office-installed-on-vm.png)

### 3.2 Send a test email from Outlook

From the first user's Outlook, sent a message to the second user's mailbox. This is the moment of truth: if mail flows internally, the tenant is functionally alive.

![Outlook test email composed and sent](images/12-outlook-send-test-email.png)

### 3.3 Confirm delivery in the second mailbox

Logged into the second user's mailbox via Outlook on the Web (the browser version of Outlook, no install needed) and verified the message arrived.

![Logging into the second user's mailbox via the web](images/13-second-user-mailbox-login.png)
![Email delivery confirmed in the second user's inbox](images/14-email-delivery-confirmed.png)

End to end mail flow works between users.

## Workstream 4: Exchange Online: Shared Mailbox, Distribution List, and Anti Malware

Email is the riskiest service in any tenant. It is how staff work and how attackers get in. For a healthcare clinic, the email surface is also where most patient information ends up: appointment confirmations, referral letters, lab results forwarded from the hospital. Locking this down is the single highest leverage move in the project.

### 4.1 Create a shared mailbox

From the **Exchange Admin Center**, created `info@` as a shared mailbox and granted both pilot users *Full Access* and *Send As* permissions. Now both Katy at reception and Mike the office manager can read patient inquiries that come in to `info@meekcloud.com` and reply on behalf of the clinic from the same address. No license needed for the shared mailbox itself, which keeps cost down for a small practice.

![Shared mailbox created](images/15-shared-mailbox-created.png)
![Both pilot users granted access to the shared mailbox](images/16-shared-mailbox-access-granted.png)

### 4.2 Create a distribution list

Created `team@` as a distribution list and added both pilot users as members. One email to that address now lands in both users' inboxes. This is how the clinic's online booking system, lab partners, and pharmacy faxes route notifications to "the front desk team" without having to remember individual addresses.

![Distribution list created with both users as members](images/17-distribution-list-created.png)

### 4.3 Test the email routing

Sent a message addressed to both the distribution list and the shared mailbox, then confirmed it landed where it should. Two different paths, two different patterns, both verified.

![Test email sent to the distribution list and shared mailbox](images/18-email-sent-to-dist-and-shared.png)
![Message received in the shared mailbox](images/19-email-received-shared-mailbox.png)
![Same message received by distribution list members](images/20-email-received-dist-members.png)

### 4.4 Review anti malware policy

Pulled up the default **anti malware policy** in Microsoft Defender for Office 365 and reviewed the three sections that matter most:

- **Overview** confirms the policy is enabled and applied to all recipients by default.
- **Actions** controls what Defender does with infected attachments (quarantine vs block).
- **Notifications** controls who gets emailed when malware is detected (admins, senders, recipients).

For a healthcare clinic the notification side matters: when malware is detected in an inbound email pretending to be from a referring physician, the right person needs to know within minutes, not when someone happens to log in to the admin portal next week.

![Anti malware policy overview](images/21-anti-malware-policy-overview.png)
![Anti malware policy actions section](images/22-anti-malware-policy-actions.png)
![Anti malware policy notifications section](images/23-anti-malware-policy-notifications.png)

## Workstream 5: SharePoint and OneDrive

The collaboration tier. Where company files actually live. For a clinic this is policies, training documents, intake form templates, the PHIPA compliance binder, the hand washing protocol poster, and so on. Not patient charts (those live in the EMR), but everything that surrounds running the practice.

### 5.1 Confirm the active SharePoint site

The default tenant site is up and reachable, proof that SharePoint Online provisioned correctly when the tenant was created. Nothing exotic here, but worth confirming before building on top of it.

![Active SharePoint site confirmed](images/24-sharepoint-active-site.png)

### 5.2 Create a document library site

Spun up a new SharePoint document library site and added both pilot users as members. This becomes the home for the clinic's training documents, policies, and shared templates. Permissions are scoped to the team, so the cleaning service that comes in after hours and shares the WiFi cannot stumble onto the staff handbook.

![New document library site created and users added](images/25-document-library-created.png)

### 5.3 Lock down OneDrive sharing

Changed the OneDrive sharing policy at the org level so that files can only be shared with **people inside the organization**. Anonymous links and external sharing are off.

This is the single most important data leak control in a small M365 tenant. Without it, any user can paste a "share with anyone who has the link" URL into a public chat, an email to the wrong recipient, or a help forum post. For a clinic where OneDrive may end up holding scanned referral forms, intake documents, or HR paperwork, that is a PHIPA breach waiting to happen. With the policy on, even a careless user cannot create a shareable link that works outside the clinic.

![OneDrive sharing restricted to internal users only](images/26-onedrive-sharing-policy-internal.png)

## What's Now Running

After the five workstreams, the tenant goes from "fresh signup" to "ready for a small clinic to actually work in":

- Branded admin experience with helpdesk info and a controlled release ring
- Two licensed users provisioned via reusable PowerShell scripts (the same script handles user 3 through user 50)
- Office installed and mail flow verified end to end
- Shared mailbox plus distribution list configured for `info@` and `team@` workflows
- Anti malware policy reviewed and active across the tenant
- SharePoint site live, OneDrive sharing locked to the organisation

A four physician clinic with eight staff members can open Monday morning on this build.

## Troubleshooting

A few things to know that are not in the official Microsoft documentation. Documenting them so the next IT consultant who picks up a small clinic engagement does not lose half a day.

### Trial license vs paid license behavior

Microsoft 365 Business Standard trials and paid licenses behave identically in the admin portal but the trial expires in 30 days. If you are doing a build out for a real client, talk to them about converting to paid before any production data lands in the tenant. Migrating data out of an expired trial is technically possible but painful. I would rather hand the client a clean transition than scramble at day 28.

### Microsoft Graph PowerShell scopes

`Connect-MgGraph` defaults to a minimal scope set that does not include user creation. The first time I ran `New-MgUser` I got a permission error. The fix is to explicitly request the right scopes at connect time:

```powershell
Connect-MgGraph -Scopes "User.ReadWrite.All", "Group.ReadWrite.All", "Directory.ReadWrite.All", "Organization.Read.All"
```

You will get an admin consent prompt the first time. Approve it once and the scopes persist for that session.

### License assignment via PowerShell needs the SKU ID, not the name

`Set-MgUserLicense` expects a license SKU ID (a GUID), not the friendly product name. To find the right one:

```powershell
Get-MgSubscribedSku | Select SkuPartNumber, SkuId
```

Look for `O365_BUSINESS_STANDARD` or similar in the output, and use the matching SkuId in the assignment command. Microsoft's docs example uses a hardcoded GUID that does not match every tenant.

### Default anti malware policy is permissive by design

The out of the box policy is set to deliver suspicious attachments to recipients with a warning, not quarantine them. For a healthcare clinic that is too lenient. The fix is to clone the default policy, set Actions to "Quarantine the message", and confirm Notifications are routed to a real admin mailbox (not just `admin@yourtenant.onmicrosoft.com` which nobody reads). I left the default policy in place for this build to keep the screenshots representative of what an admin actually sees on first log in, but the README would call out tightening this for a production handover.

### OneDrive external sharing change takes time to propagate

After flipping the org level sharing policy to "Only people in your organization", existing OneDrive shared links that were created before the change do not stop working immediately. Microsoft's documentation says the policy applies going forward. To revoke existing external links, you have to either run a SharePoint PowerShell script that audits and removes them, or manually go user by user. For a clinic this is worth doing as a one time cleanup pass at the end of the engagement.

## Cross References

This project is part of a healthcare and enterprise IT series exploring how the same Microsoft platform stack scales across organization size.

[**Project 11: HelpDesk Zero Touch**](../11-helpdesk-zero-touch/) is the automated IT operations layer that would run on top of this tenant once the clinic grows beyond the point where the office manager can handle every helpdesk request. Identity lifecycle, AI ticket triage, and permission drift detection: all of those workflows assume a tenant that looks like the one this project deploys.

[**Project 13: Microsoft 365 Enterprise Deployment**](../13-m365-enterprise-deployment/) is the same exercise scaled to 300 users on the Microsoft 365 E5 plan, with Defender for Office 365, Purview Insider Risk, DLP, audit, and Power Automate driven monthly reporting. Where Project 12 is the four physician clinic in Mississauga, Project 13 is the regional health authority that owns 12 such clinics. Same identity model, same security stack, vastly different compliance and reporting surface.

[**Project 10: Prompt Guardian**](../10-prompt-guardian/) intercepts AI prompts at the browser level before sensitive PHI reaches a public LLM. As clinics increasingly use ChatGPT or Copilot for documentation drafts, this becomes the missing piece between the Project 12 tenant and the public AI services that staff use anyway.

The four projects together cover the spine of healthcare IT: tenant deployment at two scales, AI guardrails on user behaviour, and automated support.

## What I Would Add Next

Things deliberately out of scope for this build that would be the natural next sprint with Sarah's clinic:

- **Conditional Access policies** to require MFA on every login and block sign in attempts from outside Canada. This is the highest leverage security upgrade after the OneDrive lockdown and costs nothing extra on Business Standard.
- **Multi Factor Authentication** rolled out to all users, not just admins. Most small clinic breaches start with a phished password, and MFA stops 99 percent of those attacks.
- **Data Loss Prevention** policies to auto detect SINs, OHIP card numbers, or credit card numbers in outgoing email. PHIPA breach prevention as a default behaviour.
- **Intune device management** so the clinic can wipe a stolen laptop remotely and enforce disk encryption on every device that touches patient data.
- **Backup of M365 data** to a third party tool. Microsoft replicates data for availability but does not back it up against accidental deletion or ransomware. For a clinic, an Office 365 backup product like Veeam or Druva runs around 3 to 5 USD per user per month.
- **Defender for Business** upgrade to extend protection from email to laptops and mobile devices.

## Tech Stack

| Layer | Technology |
|---|---|
| Tenant | Microsoft 365 Business Standard (trial) |
| Admin tooling | Microsoft 365 Admin Center, Exchange Admin Center, SharePoint Admin Center |
| Automation | Microsoft Graph PowerShell SDK (Microsoft.Graph module) |
| Productivity | Microsoft 365 Apps for enterprise (Word, Excel, Outlook, Teams) |
| Email infrastructure | Exchange Online (mailboxes, shared mailbox, distribution list) |
| Email security | Microsoft Defender for Office 365 (anti malware policy) |
| Collaboration | SharePoint Online, OneDrive for Business |
| Test environment | Windows 11 virtual machine for Office install testing |

## Status

Tenant built. Pilot users live. Email flow tested. SharePoint and OneDrive configured. Anti malware policy reviewed.

Ready to onboard the rest of Sarah's clinic staff using the same PowerShell scripts. Ready for handover to whatever MSP picks up the long term support contract.

---

Built by MEEK as part of an Azure cloud portfolio targeting healthcare IT, MSP, and Microsoft partner roles in Toronto, Newfoundland, and Ohio.
