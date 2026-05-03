# Microsoft 365 Tenant Deployment for a Small Business

> End-to-end build-out of a Microsoft 365 environment for **MeekCloud Services** — a fictional small business — covering tenant branding, identity, licensing, email infrastructure, malware protection, and SharePoint/OneDrive collaboration. Every step is done in a real M365 tenant (not a simulator) and documented with screenshots.

This is the kind of work a small business pays an IT consultant or a junior cloud administrator to deliver in their first week on the job. It's the foundation every other Microsoft 365 service sits on top of.

---

## The Scenario

MeekCloud Services has just signed up for Microsoft 365. They've bought a handful of Business Standard licenses and need someone to actually *configure* the tenant before staff can start working. The brief from the owner:

> "Make it look like ours, get our two pilot users on it, set up our shared inbox and team distribution list, lock down our anti-malware and file sharing, and give us a SharePoint site for training documents. Don't leave anything on defaults that shouldn't be."

This repo documents how that brief was delivered, in five workstreams.

---

## Glossary (plain-English version)

A few words that come up a lot in this project, explained in normal language:

- **Tenant** — your organisation's own private space inside Microsoft 365. Two different companies on M365 each have their own tenant; they don't see each other's data.
- **Microsoft 365 Admin Center** — the main website (admin.cloud.microsoft) where the IT admin manages everything.
- **PowerShell** — Microsoft's command-line tool. Instead of clicking buttons in a web page, you type instructions and it does them. Faster for repetitive jobs (like creating 50 users at once).
- **License** — a "seat" you've paid Microsoft for. A license decides *which* M365 apps a user can use (Word, Outlook, Teams, etc.). No license = the user can sign in but can't actually use anything.
- **Exchange** — the part of M365 that handles email. The Exchange Admin Center is where you manage mailboxes, distribution lists, anti-spam, etc.
- **Shared mailbox** — one inbox that several people can read and reply from (e.g., `support@meekcloud.com`). Cheaper than giving each support agent their own license.
- **Distribution list (DL)** — an email address that fans out to a group of people. Email `team@meekcloud.com` once → everyone on the list gets it.
- **SharePoint** — Microsoft's website-and-document-library platform. Internal team sites, company intranet pages, document storage with permissions.
- **OneDrive** — personal cloud file storage that comes with each user's M365 license. Like Dropbox, but built into Windows.
- **Anti-malware policy** — the rules Microsoft Defender uses to scan incoming email for viruses and decide what to do with bad attachments.

---

## Workstream 1 — Brand the Tenant

A fresh M365 tenant looks the same as everyone else's. The first job is to make it feel like *MeekCloud's* environment so users trust what they're logging into.

### 1.1 Upload the company logo

The custom logo now appears in the top-left of the Microsoft 365 admin center (and on staff sign-in pages).

![Tenant logo uploaded and visible in the admin center](images/01-tenant-logo-uploaded.png)

### 1.2 Apply a custom color theme

Switched the admin center's accent colour and header to match MeekCloud's brand palette. Small touch, but it tells employees they're inside the right place.

![Custom color theme applied across the admin center](images/02-color-theme-customized.png)

### 1.3 Make the logo clickable

Configured the logo so that clicking it opens MeekCloud's company URL — useful for quickly jumping to internal resources from the admin center.

![Logo configured to open the company URL when clicked](images/03-logo-link-configured.png)

### 1.4 Add helpdesk contact info

If a user runs into trouble, the M365 portal now shows them how to reach internal IT support — phone, email, and helpdesk URL.

![Helpdesk contact information set in the organization profile](images/04-helpdesk-contact-set.png)

### 1.5 Pick early-release pilot users

Selected two users to receive Microsoft feature updates *before* they roll out to the wider organisation. This is a "release ring" — a small, controlled group that catches breaking changes early.

![Two users selected for early Microsoft feature releases](images/05-early-release-users-selected.png)

---

## Workstream 2 — Identity & Licensing via PowerShell

Clicking through the admin UI is fine for one or two users. But real environments use PowerShell because it's repeatable and auditable — you can save a script and run it again next month.

### 2.1 Install the Microsoft Graph PowerShell module and connect

Installed the **Microsoft.Graph** PowerShell module on the admin workstation, then ran `Connect-MgGraph` with the right *scopes* (permission flags). After signing in once, every subsequent command runs against the live tenant.

![Installing the Microsoft Graph PowerShell module](images/06-powershell-module-install.png)
![Connected to Microsoft 365 with Connect-MgGraph](images/07-powershell-connect-to-m365.png)

### 2.2 Create the two pilot users

Used `New-MgUser` to provision two accounts. Doing it in PowerShell means the same script can be reused later to bulk-create users from a CSV.

![First pilot user (Katy Price) created via PowerShell](images/08-powershell-create-user-katy.png)
![Second pilot user created via PowerShell](images/09-powershell-create-user-second.png)

### 2.3 Assign licenses

A user without a license is just a name in the directory — they can't open Outlook or Word. Used `Set-MgUserLicense` to attach a Microsoft 365 trial license to each pilot account.

![Microsoft 365 license assigned to the pilot users with PowerShell](images/10-powershell-assign-license.png)

---

## Workstream 3 — Install and Test Microsoft 365 Apps

Provisioning users is meaningless until someone actually uses them. This workstream proves the licenses work end-to-end.

### 3.1 Install Office on a Windows VM

Installed the full Microsoft 365 Apps for enterprise package on a Windows virtual machine and signed in with the first pilot user to *activate* the install (Office contacts Microsoft to confirm there's a license tied to the account).

![Office installed and activated on the test VM](images/11-office-installed-on-vm.png)

### 3.2 Send a test email from Outlook

From the first user's Outlook, sent a message to the second user's mailbox.

![Outlook test email composed and sent](images/12-outlook-send-test-email.png)

### 3.3 Confirm delivery in the second mailbox

Logged into the second user's mailbox via Outlook on the Web (the browser version of Outlook, no install needed) and verified the message arrived.

![Logging into the second user's mailbox via the web](images/13-second-user-mailbox-login.png)
![Email delivery confirmed in the second user's inbox](images/14-email-delivery-confirmed.png)

End-to-end mail flow works between MeekCloud users.

---

## Workstream 4 — Exchange: Shared Mailbox, Distribution List, and Anti-Malware

Email is the riskiest service in any tenant — both because it's how people work and because it's how attackers get in.

### 4.1 Create a shared mailbox

From the **Exchange Admin Center**, created `meek-Shared` and granted both pilot users *Full Access* and *Send As* permissions. They can now both read it and reply *as* the shared address.

![Shared mailbox created](images/15-shared-mailbox-created.png)
![Both pilot users granted access to the shared mailbox](images/16-shared-mailbox-access-granted.png)

### 4.2 Create a distribution list

Created `meek-Dist` and added both pilot users as members. One email to that address now lands in both users' inboxes.

![Distribution list created with both users as members](images/17-distribution-list-created.png)

### 4.3 Test the email routing

Sent a message addressed to *both* the distribution list and the shared mailbox, then confirmed it landed where it should.

![Test email sent to the distribution list and shared mailbox](images/18-email-sent-to-dist-and-shared.png)
![Message received in the shared mailbox](images/19-email-received-shared-mailbox.png)
![Same message received by distribution list members](images/20-email-received-dist-members.png)

### 4.4 Review anti-malware policy

Pulled up the default **anti-malware policy** in Microsoft Defender for Office 365 and reviewed the three sections that matter most:

- **Overview** — confirms the policy is enabled and applied to all recipients by default.
- **Actions** — what Defender does with infected attachments (quarantine vs. block).
- **Notifications** — who gets emailed when malware is detected (admins, senders, recipients).

![Anti-malware policy overview](images/21-anti-malware-policy-overview.png)
![Anti-malware policy actions section](images/22-anti-malware-policy-actions.png)
![Anti-malware policy notifications section](images/23-anti-malware-policy-notifications.png)

---

## Workstream 5 — SharePoint and OneDrive

The collaboration tier — where company files actually live.

### 5.1 Confirm the active SharePoint site

The default tenant site (Paschal's Training Center, used as a sample collaboration hub) is up and reachable — proof that SharePoint Online provisioned correctly.

![Active SharePoint site confirmed](images/24-sharepoint-active-site.png)

### 5.2 Create a document library site

Spun up a new SharePoint document library site for MeekCloud and added both pilot users as members. This is where shared team files will live going forward.

![New document library site created and users added](images/25-document-library-created.png)

### 5.3 Lock down OneDrive sharing

Changed the OneDrive sharing policy so that files can only be shared with **people inside MeekCloud**. Anonymous links and external sharing are off. This is the single most important data-leak control in a small M365 tenant — without it, any user can paste a "share with anyone" link into a public chat.

![OneDrive sharing restricted to internal users only](images/26-onedrive-sharing-policy-internal.png)

---

## What's Now Running

After the five workstreams, the tenant goes from "fresh signup" to "ready for a small business to actually work in":

- Branded admin experience with helpdesk info and a controlled release ring
- Two licensed users provisioned via reusable PowerShell scripts
- Office installed and mail flow verified
- Shared mailbox + distribution list configured for team collaboration
- Anti-malware policy reviewed and active
- SharePoint site live and OneDrive sharing locked to the organisation

---

## What I'd Add Next

Things deliberately out of scope for this build that would be the natural next sprint:

- **Conditional Access** — rules like "block sign-in from outside Canada" or "require MFA on every login."
- **Multi-Factor Authentication (MFA)** rolled out to all users, not just admins.
- **Data Loss Prevention (DLP)** policies — auto-detect credit card numbers or SINs in outgoing email.
- **Intune / device management** — control which laptops are allowed to access company data.
- **Backup of M365 data** to a third-party tool (Microsoft replicates data but doesn't back it up against accidental deletion).

---

## Tech Stack

- Microsoft 365 (Business Standard trial)
- Microsoft 365 Admin Center
- Exchange Admin Center
- SharePoint Online & OneDrive for Business
- Microsoft Defender for Office 365 (anti-malware)
- Microsoft Graph PowerShell SDK (`Microsoft.Graph` module)
- Windows 11 virtual machine (for Office install testing)
