# 10 Prompt Guardian: Real Time AI Prompt Interception for Regulated Environments

## The Problem

A hospital IT coordinator pastes a patient discharge summary into ChatGPT to "improve the wording." That summary includes the patient's name, date of birth, diagnosis, and provider notes. In one click, Protected Health Information leaves the organization with no audit trail, no alert, and no compliance record.

This is not hypothetical. 38% of employees acknowledge sharing sensitive work data with AI tools without permission. Samsung engineers leaked proprietary source code through ChatGPT. Hospitals face $50,000 per HIPAA violation. The existing solutions, enterprise DLP tools costing $50,000 to $300,000 per year, do not even monitor AI prompts at the browser level.

Microsoft announced shadow AI protection at RSAC 2026 but it only works in Edge with E5 licensing at $57 per user per month. If someone opens Chrome, it is useless.

## The Solution

Prompt Guardian intercepts AI prompts at the moment of submission, before data leaves the browser. It uses Azure OpenAI to understand context (not just keywords), classifies content as ALLOW, REDACT, or BLOCK, and creates an immutable audit trail for every decision.

The key differentiator is the justification override flow. Instead of forcing users to bypass the system entirely, Prompt Guardian gives them a controlled way to proceed. The override is logged, the manager is notified automatically, and the audit trail says "User submitted PHI with justification: medical necessity." That is compliance defensibility.

Cost: approximately $150 to $200 per month on Azure consumption. Not $50,000 to $300,000 per year.

## Architecture

Seven layers working together:

1. **Browser Interceptor** Chrome extension (Manifest V3) captures prompts before submission to ChatGPT, Claude, or Copilot
2. **AI Classification Engine** Azure Function plus GPT 4o analyzes content for PHI, PII, credentials, financial data, legal privilege
3. **Decision Engine** Returns ALLOW, REDACT, or BLOCK with confidence score and flagged content
4. **Justification Override** User selects reason, types justification, manager auto notified via Logic App
5. **Immutable Audit Trail** Append only Azure Blob Storage, stores hashes only, no raw PHI
6. **Compliance Dashboard** Live web dashboard reading real audit data from Azure
7. **Notification System** Logic App sends manager email on every override

## Live Infrastructure

All deployed via Terraform:

| Resource | Name | Purpose |
|---|---|---|
| Resource Group | rg-promptguard-dev-061l6f | All project resources (East US 2) |
| Function App | fn-promptguard-061l6f | Three endpoints: classify, override, audit summary |
| Azure OpenAI | oai-promptguard-061l6f | GPT 4o classification engine (East US) |
| Key Vault | kv-promptguard-061l6f | API keys and connection strings |
| Storage Account | stpromptguard061l6f | Immutable audit logs container |
| Logic App | logic-override-notify-061l6f | Manager email notification on override |

## Implementation

### Phase 1 Backend MVP

The classify endpoint receives a prompt, sends it to GPT 4o with a healthcare specific system prompt, and returns the classification with flagged content, redacted version, and recommended action. Every classification is logged to Blob Storage as an immutable audit entry containing only the prompt hash, never raw content.

![Resource Group](./screenshots/01-resource-group-overview.png)
*All Terraform deployed resources in rg-promptguard-dev-061l6f.*

![Storage Audit Container](./screenshots/02-storage-audit-logs-container.png)
*Append only audit logs container storing immutable classification records.*

![Key Vault Secrets](./screenshots/03-key-vault-secrets.png.png)
*All credentials stored in Key Vault. Zero secrets in code.*

![OpenAI Deployment](./screenshots/04-openai-model-deployment.png)
*GPT 4o deployed and active in Azure AI Foundry.*

![Function App](./screenshots/05-function-app-overview.png)
*Function App running with three live endpoints.*

![Test Suite](./screenshots/09-test-suite-summary.png)
*93.3% accuracy on 30 prompt test suite. CREDENTIALS 100%, LEGAL 100%, EDGE CASE 100%.*

### Phase 2 Simulation UI

A nurse friendly interface where anyone can paste a prompt and see the classification in real time.

![Sim UI ALLOW](./screenshots/10-sim-ui-allow-clean.png)
*Safe prompt passes through.*

![Sim UI BLOCK](./screenshots/11-sim-ui-block-phi.png)
*Discharge summary with patient name, DOB, MRN blocked. Flagged content highlighted.*

![Sim UI REDACT](./screenshots/12-sim-ui-redact-pii.png)
*Client email with sensitive fields stripped. Safe version provided.*

![Sim UI Edge Case](./screenshots/13-sim-ui-allow-edge-case.png)
*"Generate fake patient data" allowed. A DLP would block this. Prompt Guardian understands the user wants synthetic data.*

### Phase 3 Chrome Extension

Manifest V3 extension intercepts submit on ChatGPT, Claude, and Copilot. Modal appears before data leaves the browser.

![Extension Loaded](./screenshots/14-chrome-extension-loaded.png)
*Extension loaded in Chrome.*

![Extension Block](./screenshots/15-extension-intercept-block.png)
*Guardian modal blocking PHI before submission.*

![Extension Popup](./screenshots/16-extension-popup-active.png)
*Protection Active with toggle control.*

### Phase 4 Override System

User clicks Override with Justification, selects a reason, types an explanation. Override is logged and manager receives automatic email via Logic App.

![ChatGPT Block](./screenshots/17-chatgpt-block-modal.png)
*Guardian blocking PHI on live ChatGPT.*

![Override Form](./screenshots/18-chatgpt-override-form.png)
*Justification required before proceeding.*

![Override Email](./screenshots/19-override-email-received.png)
*Manager notified automatically within seconds.*

![Audit Override](./screenshots/20-audit-trail-override-entry.png)
*Override logged with reason, justification, timestamp, and prompt hash.*

### Phase 5 Compliance Dashboard

Live dashboard pulling real audit data from Azure via the audit summary endpoint.

![Dashboard KPIs](./screenshots/21-dashboard-kpi-overview.png)
*99 total scans, 51 blocked, 11 redacted, 28 allowed, 9 overrides. Real data from Azure.*

![AI Insights](./screenshots/22-dashboard-ai-insights.png)
*48 PHI exposure attempts intercepted. Override patterns analyzed. Credential exposure flagged.*

![Recent Events](./screenshots/23-dashboard-recent-events.png)
*Live event log from Azure Blob Storage with real timestamps, users, and decisions.*

## What Makes This Different

| Enterprise DLP | Prompt Guardian |
|---|---|
| Monitors network traffic | Intercepts at browser submit button |
| Keyword matching | AI understands context |
| Allow or block only | ALLOW, REDACT, or BLOCK |
| Users bypass the system | Override keeps users inside the system |
| $50,000 to $300,000 per year | Approximately $2,400 per year |
| Edge only (Microsoft) | Any browser |

## Technologies Used

Terraform, Azure Functions (Python), Azure OpenAI (GPT 4o), Azure Blob Storage, Azure Key Vault, Azure Logic Apps, Chrome Extension (Manifest V3), JavaScript, HTML/CSS, Managed Identity
