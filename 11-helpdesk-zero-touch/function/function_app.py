import azure.functions as func
import json
import logging
import os
import hashlib
from datetime import datetime, timezone
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient
import uuid

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# ============================================================
# SHARED UTILITIES
# ============================================================

def get_openai_client():
    return AzureOpenAI(
        azure_endpoint=os.environ.get("OPENAI_ENDPOINT"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        api_version="2024-02-01"
    )

def write_log(container_name, data, prefix="log"):
    conn = os.environ.get("STORAGE_CONNECTION_STRING")
    if not conn:
        return None
    client = BlobServiceClient.from_connection_string(conn)
    container = client.get_container_client(container_name)
    ts = datetime.now(timezone.utc)
    blob_name = f"{ts.strftime('%Y/%m/%d')}/{prefix}-{ts.strftime('%H%M%S')}-{uuid.uuid4().hex[:8]}.json"
    container.upload_blob(name=blob_name, data=json.dumps(data, indent=2), overwrite=False)
    return blob_name

def cors_response(status=200):
    return func.HttpResponse(status_code=status, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    })

def json_response(data, status=200):
    return func.HttpResponse(
        json.dumps(data, indent=2),
        status_code=status,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )

# ============================================================
# TRACK 1: IDENTITY LIFECYCLE (Onboarding / Offboarding)
# ============================================================

ONBOARD_TASKS = [
    "Create Entra ID user account",
    "Assign Microsoft 365 E3 license",
    "Add to department security group",
    "Provision Exchange Online mailbox",
    "Map shared network drives",
    "Enable MFA registration",
    "Send welcome email to manager"
]

OFFBOARD_TASKS = [
    "Disable user account in Entra ID",
    "Revoke all active sessions",
    "Remove from all security groups",
    "Reclaim Microsoft 365 license",
    "Transfer mailbox ownership to manager",
    "Revoke VPN and remote access",
    "Archive user data to compliance hold",
    "Generate offboarding audit report"
]

@app.route(route="identity/onboard", methods=["POST", "OPTIONS"])
def identity_onboard(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_response()

    try:
        body = req.get_json()
    except ValueError:
        return json_response({"error": "Invalid JSON"}, 400)

    user_name = body.get("user_name", "").strip()
    department = body.get("department", "").strip()
    role = body.get("role", "").strip()
    manager = body.get("manager", "").strip()
    start_date = body.get("start_date", "").strip()

    if not user_name or not department:
        return json_response({"error": "user_name and department are required"}, 400)

    # Simulate onboarding execution
    results = []
    for task in ONBOARD_TASKS:
        results.append({
            "task": task,
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"Executed for {user_name} in {department}"
        })

    # Generate AI summary
    client = get_openai_client()
    deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")

    prompt = f"""Summarize this employee onboarding in 2-3 sentences for an IT manager:
Employee: {user_name}
Department: {department}
Role: {role}
Manager: {manager}
Start Date: {start_date}
Tasks completed: {', '.join(ONBOARD_TASKS)}
All tasks succeeded with zero errors."""

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are an IT operations assistant. Write concise, professional summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        ai_summary = response.choices[0].message.content.strip()
    except Exception as e:
        ai_summary = f"Onboarding completed for {user_name}. All {len(ONBOARD_TASKS)} tasks executed successfully."
        logging.warning(f"AI summary failed: {e}")

    # Write audit log
    log_data = {
        "event_type": "onboarding",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_name": user_name,
        "department": department,
        "role": role,
        "manager": manager,
        "start_date": start_date,
        "tasks_completed": len(results),
        "tasks_failed": 0,
        "task_details": results,
        "ai_summary": ai_summary
    }
    audit_ref = write_log(os.environ.get("IDENTITY_LOG_CONTAINER", "identity-logs"), log_data, "onboard")

    return json_response({
        "status": "onboarding_complete",
        "user_name": user_name,
        "department": department,
        "tasks_completed": len(results),
        "tasks_failed": 0,
        "ai_summary": ai_summary,
        "audit_ref": audit_ref
    })


@app.route(route="identity/offboard", methods=["POST", "OPTIONS"])
def identity_offboard(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_response()

    try:
        body = req.get_json()
    except ValueError:
        return json_response({"error": "Invalid JSON"}, 400)

    user_name = body.get("user_name", "").strip()
    department = body.get("department", "").strip()
    reason = body.get("reason", "voluntary_resignation").strip()
    last_day = body.get("last_day", "").strip()

    if not user_name:
        return json_response({"error": "user_name is required"}, 400)

    results = []
    for task in OFFBOARD_TASKS:
        results.append({
            "task": task,
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    # AI summary
    client = get_openai_client()
    deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")

    prompt = f"""Summarize this employee offboarding in 2-3 sentences for an IT manager and compliance officer:
Employee: {user_name}
Department: {department}
Reason: {reason}
Last Day: {last_day}
Tasks completed: {', '.join(OFFBOARD_TASKS)}
All access has been revoked. No tasks failed."""

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are an IT operations assistant. Write concise summaries emphasizing security and compliance."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        ai_summary = response.choices[0].message.content.strip()
    except Exception as e:
        ai_summary = f"Offboarding completed for {user_name}. All {len(OFFBOARD_TASKS)} deprovisioning tasks executed. Access fully revoked."
        logging.warning(f"AI summary failed: {e}")

    log_data = {
        "event_type": "offboarding",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_name": user_name,
        "department": department,
        "reason": reason,
        "last_day": last_day,
        "tasks_completed": len(results),
        "tasks_failed": 0,
        "task_details": results,
        "ai_summary": ai_summary,
        "compliance_note": "All access revoked, data archived, audit trail created"
    }
    audit_ref = write_log(os.environ.get("IDENTITY_LOG_CONTAINER", "identity-logs"), log_data, "offboard")

    return json_response({
        "status": "offboarding_complete",
        "user_name": user_name,
        "tasks_completed": len(results),
        "tasks_failed": 0,
        "access_revoked": True,
        "ai_summary": ai_summary,
        "audit_ref": audit_ref
    })


# ============================================================
# TRACK 2: AI TICKET TRIAGE + KNOWLEDGE DEFLECTION
# ============================================================

TRIAGE_SYSTEM_PROMPT = """You are an IT helpdesk triage AI for a healthcare organization.

Analyze the support ticket and return ONLY a JSON object with no markdown or explanation.

Classify the ticket into one of these categories:
- PASSWORD_RESET: Password locked, expired, forgotten
- ACCESS_REQUEST: Need access to app, folder, system, VPN
- HARDWARE: Device broken, slow, needs replacement
- SOFTWARE: App crash, install request, update issue
- NETWORK: WiFi, VPN, connectivity, printing
- EMAIL: Outlook, calendar, shared mailbox
- SECURITY: Phishing report, suspicious activity, data concern
- OTHER: Anything that does not fit above

Assign priority:
- P1_CRITICAL: System down, multiple users affected, patient safety risk
- P2_HIGH: Single user blocked from working, time sensitive
- P3_MEDIUM: Inconvenient but has workaround
- P4_LOW: Nice to have, no urgency

Check if a knowledge base article could resolve it without a technician.

Return this exact JSON:
{
  "category": "one of the categories above",
  "priority": "P1_CRITICAL | P2_HIGH | P3_MEDIUM | P4_LOW",
  "summary": "one sentence plain English summary of the issue",
  "suggested_resolution": "what the technician should try first, in plain English",
  "kb_deflectable": true or false,
  "kb_article_suggestion": "if deflectable, describe the KB article title and content that would solve this, otherwise null",
  "estimated_resolution_minutes": integer estimate,
  "route_to": "tier1 | tier2 | tier3 | security_team | network_team",
  "tags": ["list", "of", "relevant", "tags"]
}"""

@app.route(route="triage", methods=["POST", "OPTIONS"])
def triage_ticket(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_response()

    try:
        body = req.get_json()
    except ValueError:
        return json_response({"error": "Invalid JSON"}, 400)

    ticket_text = body.get("ticket", "").strip()
    submitter = body.get("submitter", "anonymous").strip()
    ticket_id = body.get("ticket_id", f"TK-{uuid.uuid4().hex[:6].upper()}")

    if not ticket_text:
        return json_response({"error": "ticket field is required"}, 400)

    client = get_openai_client()
    deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": ticket_text}
            ],
            temperature=0.1,
            max_tokens=500
        )
        text = response.choices[0].message.content
        text = text.replace("```json", "").replace("```", "").strip()
        triage_result = json.loads(text)
    except Exception as e:
        logging.error(f"Triage failed: {e}")
        return json_response({"error": f"Triage failed: {str(e)}"}, 500)

    triage_result["ticket_id"] = ticket_id
    triage_result["submitter"] = submitter
    triage_result["original_ticket"] = ticket_text[:200]

    # Write audit log
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticket_id": ticket_id,
        "submitter": submitter,
        "ticket_text_hash": hashlib.sha256(ticket_text.encode()).hexdigest(),
        "ticket_length": len(ticket_text),
        "category": triage_result.get("category"),
        "priority": triage_result.get("priority"),
        "kb_deflectable": triage_result.get("kb_deflectable"),
        "route_to": triage_result.get("route_to"),
        "estimated_minutes": triage_result.get("estimated_resolution_minutes")
    }
    audit_ref = write_log(os.environ.get("TRIAGE_LOG_CONTAINER", "triage-logs"), log_data, "triage")
    triage_result["audit_ref"] = audit_ref

    return json_response(triage_result)


# ============================================================
# TRACK 3: PERMISSION DRIFT DETECTOR
# ============================================================

@app.route(route="drift/scan", methods=["POST", "OPTIONS"])
def drift_scan(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_response()

    # Simulate scanning users with realistic permission drift scenarios
    simulated_users = [
        {
            "user": "maria.santos@contoso.com",
            "display_name": "Maria Santos",
            "department": "Billing",
            "role": "Billing Clerk",
            "current_groups": ["Billing", "Finance-ReadOnly", "Imaging-Admin", "VPN-Users", "All-Staff"],
            "expected_groups": ["Billing", "Finance-ReadOnly", "VPN-Users", "All-Staff"],
            "excess_permissions": ["Imaging-Admin"],
            "drift_reason": "Added during server migration project 6 months ago, never revoked",
            "risk_level": "HIGH",
            "last_login": "2026-04-28T14:30:00Z"
        },
        {
            "user": "james.chen@contoso.com",
            "display_name": "James Chen",
            "department": "Nursing",
            "role": "Registered Nurse",
            "current_groups": ["Nursing", "EHR-Users", "Pharmacy-Admin", "Lab-Results-View", "All-Staff"],
            "expected_groups": ["Nursing", "EHR-Users", "Lab-Results-View", "All-Staff"],
            "excess_permissions": ["Pharmacy-Admin"],
            "drift_reason": "Temporary coverage during pharmacist leave, access not removed",
            "risk_level": "CRITICAL",
            "last_login": "2026-04-29T08:15:00Z"
        },
        {
            "user": "sarah.williams@contoso.com",
            "display_name": "Sarah Williams",
            "department": "IT",
            "role": "Former Help Desk Technician",
            "current_groups": ["IT-Support", "Domain-Admins", "Azure-Contributors", "VPN-Users", "All-Staff"],
            "expected_groups": [],
            "excess_permissions": ["IT-Support", "Domain-Admins", "Azure-Contributors", "VPN-Users", "All-Staff"],
            "drift_reason": "Employee left 11 days ago, account still active, no offboarding ticket submitted",
            "risk_level": "CRITICAL",
            "last_login": "2026-04-18T16:45:00Z"
        },
        {
            "user": "david.patel@contoso.com",
            "display_name": "David Patel",
            "department": "Radiology",
            "role": "Radiology Technologist",
            "current_groups": ["Radiology", "PACS-Users", "PACS-Admin", "Imaging-Server-RDP", "All-Staff"],
            "expected_groups": ["Radiology", "PACS-Users", "All-Staff"],
            "excess_permissions": ["PACS-Admin", "Imaging-Server-RDP"],
            "drift_reason": "Elevated access granted for PACS upgrade, not revoked after completion",
            "risk_level": "HIGH",
            "last_login": "2026-04-29T10:00:00Z"
        }
    ]

    # AI analysis
    client = get_openai_client()
    deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")

    drift_summary_prompt = f"""Analyze this permission drift scan for a healthcare organization and write a compliance report summary.

Users with permission drift detected:
{json.dumps(simulated_users, indent=2)}

Write a JSON response with:
{{
  "total_users_scanned": 247,
  "users_with_drift": {len(simulated_users)},
  "critical_findings": number of CRITICAL risk items,
  "high_findings": number of HIGH risk items,
  "compliance_status": "FAIL" or "PASS",
  "executive_summary": "2-3 sentence summary for a CISO",
  "recommendations": ["list of specific actions to take"],
  "hipaa_impact": "assessment of HIPAA compliance risk",
  "phipa_impact": "assessment of PHIPA (Ontario) compliance risk"
}}"""

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a compliance and security analyst. Provide clear, actionable findings."},
                {"role": "user", "content": drift_summary_prompt}
            ],
            temperature=0.2,
            max_tokens=600
        )
        text = response.choices[0].message.content
        text = text.replace("```json", "").replace("```", "").strip()
        ai_analysis = json.loads(text)
    except Exception as e:
        logging.error(f"Drift analysis failed: {e}")
        ai_analysis = {
            "total_users_scanned": 247,
            "users_with_drift": len(simulated_users),
            "critical_findings": 2,
            "high_findings": 2,
            "compliance_status": "FAIL",
            "executive_summary": f"Permission drift scan detected {len(simulated_users)} users with excessive access. Includes 1 departed employee with active Domain Admin access and 1 nurse with unauthorized pharmacy admin privileges.",
            "recommendations": ["Immediately disable sarah.williams account", "Remove Pharmacy-Admin from james.chen", "Remove Imaging-Admin from maria.santos", "Remove PACS-Admin and RDP from david.patel"],
            "hipaa_impact": "HIGH - Departed employee with active credentials violates HIPAA access controls",
            "phipa_impact": "HIGH - Same findings apply under Ontario PHIPA Section 12"
        }

    # Combine results
    report = {
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "scan_type": "weekly_permission_drift",
        "ai_analysis": ai_analysis,
        "drift_details": simulated_users
    }

    audit_ref = write_log(os.environ.get("DRIFT_REPORT_CONTAINER", "drift-reports"), report, "drift-scan")
    report["audit_ref"] = audit_ref

    return json_response(report)


# ============================================================
# DASHBOARD SUMMARY ENDPOINT
# ============================================================

@app.route(route="dashboard", methods=["GET", "OPTIONS"])
def dashboard_summary(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return cors_response()

    conn = os.environ.get("STORAGE_CONNECTION_STRING")
    if not conn:
        return json_response({"error": "Storage not configured"}, 500)

    try:
        blob_service = BlobServiceClient.from_connection_string(conn)
        containers = ["identity-logs", "triage-logs", "drift-reports"]
        all_events = []

        for container_name in containers:
            try:
                container = blob_service.get_container_client(container_name)
                for blob in container.list_blobs():
                    blob_client = container.get_blob_client(blob.name)
                    data = json.loads(blob_client.download_blob().readall().decode("utf-8"))
                    data["_source"] = container_name
                    data["_blob"] = blob.name
                    all_events.append(data)
            except Exception as e:
                logging.warning(f"Error reading {container_name}: {e}")

        # Summarize
        identity_events = [e for e in all_events if e.get("_source") == "identity-logs"]
        triage_events = [e for e in all_events if e.get("_source") == "triage-logs"]
        drift_events = [e for e in all_events if e.get("_source") == "drift-reports"]

        onboards = [e for e in identity_events if e.get("event_type") == "onboarding"]
        offboards = [e for e in identity_events if e.get("event_type") == "offboarding"]

        # Triage category breakdown
        triage_categories = {}
        triage_priorities = {}
        kb_deflectable_count = 0
        for t in triage_events:
            cat = t.get("category", "UNKNOWN")
            pri = t.get("priority", "UNKNOWN")
            triage_categories[cat] = triage_categories.get(cat, 0) + 1
            triage_priorities[pri] = triage_priorities.get(pri, 0) + 1
            if t.get("kb_deflectable"):
                kb_deflectable_count += 1

        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "identity": {
                "total_events": len(identity_events),
                "onboardings": len(onboards),
                "offboardings": len(offboards)
            },
            "triage": {
                "total_tickets": len(triage_events),
                "by_category": triage_categories,
                "by_priority": triage_priorities,
                "kb_deflectable": kb_deflectable_count,
                "deflection_rate": round(kb_deflectable_count / max(len(triage_events), 1) * 100, 1)
            },
            "drift": {
                "total_scans": len(drift_events),
                "latest_scan": drift_events[-1] if drift_events else None
            },
            "recent_events": sorted(all_events, key=lambda x: x.get("timestamp", ""), reverse=True)[:20]
        }

        return json_response(summary)
    except Exception as e:
        logging.error(f"Dashboard failed: {e}")
        return json_response({"error": str(e)}, 500)
