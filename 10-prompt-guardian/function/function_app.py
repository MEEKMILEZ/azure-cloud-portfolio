import azure.functions as func
import json
import logging
import os
import hashlib
from datetime import datetime, timezone
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient
import uuid
import urllib.request

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

SYSTEM_PROMPT = """You are a data classification engine for a healthcare compliance system.

Analyze the prompt for sensitive content and return ONLY a JSON object — no markdown, no explanation.

Classify content into these categories:
- PHI: Protected Health Information (patient names, DOB, MRN, SSN, diagnosis, medications, lab results, treatment details)
- PII: Personally Identifiable Information (employee names+contact, SSN not in healthcare context)
- CREDENTIALS: Passwords, API keys, connection strings, access tokens, secrets
- FINANCIAL: Credit card numbers, bank accounts, routing numbers, wire transfers, detailed financial records
- LEGAL: Attorney-client privileged content, active litigation details, breach notifications

Decide on one of three actions:
- ALLOW: No sensitive content detected. Safe to proceed.
- REDACT: Sensitive content present but the underlying request is legitimate. Strip the sensitive fields, allow the intent.
- BLOCK: Sensitive content that should not leave the organization. No safe version possible.

IMPORTANT — understand intent, not just keywords:
- "Generate fake patient data for testing" = ALLOW (no real data being sent out)
- "What are HIPAA penalties?" = ALLOW (educational)
- "Anonymize this case study: 52yo female with X" = REDACT (help them, remove identifiers)
- "Translate this discharge summary: Patient Jane Smith DOB..." = BLOCK (real PHI being sent out)
- Clinical vignettes with no real patient identifiers = ALLOW

Return this exact JSON structure:
{
  "action": "ALLOW" | "REDACT" | "BLOCK",
  "category": "CLEAN" | "PHI" | "PII" | "CREDENTIALS" | "FINANCIAL" | "LEGAL",
  "severity": "none" | "low" | "medium" | "high" | "critical",
  "confidence": "low" | "medium" | "high",
  "flagged_content": ["list of specific flagged phrases or field names, empty if ALLOW"],
  "redacted_prompt": "the prompt with sensitive fields replaced by [REDACTED-TYPE] placeholders, null if action is not REDACT",
  "summary": "one sentence explaining the decision in plain English",
  "recommended_action": "specific guidance for the user in one sentence"
}"""


def get_openai_client():
    return AzureOpenAI(
        azure_endpoint=os.environ.get("OPENAI_ENDPOINT"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        api_version="2024-02-01"
    )


def classify_prompt(prompt_text):
    client = get_openai_client()
    deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt_text}
        ],
        temperature=0.1,
        max_tokens=600
    )
    text = response.choices[0].message.content
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def write_audit_log(prompt_text, classification, user_id="anonymous", override=False, override_reason=None, override_justification=None):
    connection_string = os.environ.get("STORAGE_CONNECTION_STRING")
    container_name = os.environ.get("AUDIT_CONTAINER", "audit-logs")
    if not connection_string:
        return None

    blob_client = BlobServiceClient.from_connection_string(connection_string)
    container = blob_client.get_container_client(container_name)

    timestamp = datetime.now(timezone.utc)
    date_str = timestamp.strftime("%Y/%m/%d")
    prefix = "override" if override else "audit"
    blob_name = f"{date_str}/{prefix}-{timestamp.strftime('%H%M%S')}-{uuid.uuid4().hex[:8]}.json"

    audit_entry = {
        "timestamp":              timestamp.isoformat(),
        "user_id":                user_id,
        "prompt_hash":            hashlib.sha256(prompt_text.encode()).hexdigest(),
        "prompt_length":          len(prompt_text),
        "action":                 classification.get("action"),
        "category":               classification.get("category"),
        "severity":               classification.get("severity"),
        "confidence":             classification.get("confidence"),
        "flagged_content":        classification.get("flagged_content", []),
        "summary":                classification.get("summary"),
        "override":               override,
        "override_reason":        override_reason,
        "override_justification": override_justification
    }

    container.upload_blob(name=blob_name, data=json.dumps(audit_entry, indent=2), overwrite=False)
    return blob_name


def notify_manager(override_data):
    logic_app_url = os.environ.get("OVERRIDE_LOGIC_APP_URL", "")
    if not logic_app_url:
        logging.warning("OVERRIDE_LOGIC_APP_URL not set")
        return
    try:
        # Decode any double-encoded URL characters
        logic_app_url = logic_app_url.replace("%252F", "%2F")
        payload = json.dumps(override_data).encode("utf-8")
        req = urllib.request.Request(logic_app_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=15)
        logging.info(f"Manager notified, status: {resp.status}")
    except Exception as e:
        logging.error(f"Manager notification failed: {e}")


@app.route(route="classify", methods=["POST", "OPTIONS"])
def classify(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=200, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-User-ID"
        })

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(json.dumps({"error": "Invalid JSON body"}), status_code=400, mimetype="application/json")

    prompt_text = body.get("prompt", "").strip()
    user_id = req.headers.get("X-User-ID", "anonymous")

    if not prompt_text:
        return func.HttpResponse(json.dumps({"error": "prompt field is required"}), status_code=400, mimetype="application/json")
    if len(prompt_text) > 10000:
        return func.HttpResponse(json.dumps({"error": "prompt exceeds 10,000 character limit"}), status_code=400, mimetype="application/json")

    try:
        classification = classify_prompt(prompt_text)
    except Exception as e:
        logging.error(f"Classification failed: {e}")
        return func.HttpResponse(json.dumps({"error": f"Classification failed: {str(e)}"}), status_code=500, mimetype="application/json")

    try:
        audit_blob = write_audit_log(prompt_text, classification, user_id)
        classification["audit_ref"] = audit_blob
    except Exception as e:
        logging.warning(f"Audit log failed: {e}")
        classification["audit_ref"] = None

    return func.HttpResponse(json.dumps(classification, indent=2), status_code=200, mimetype="application/json", headers={"Access-Control-Allow-Origin": "*"})


@app.route(route="override", methods=["POST", "OPTIONS"])
def override(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=200, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-User-ID"
        })

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(json.dumps({"error": "Invalid JSON body"}), status_code=400, mimetype="application/json")

    prompt_text = body.get("prompt", "").strip()
    reason = body.get("reason", "").strip()
    justification = body.get("justification", "").strip()
    original_action = body.get("original_action", "BLOCK")
    original_category = body.get("original_category", "UNKNOWN")
    original_severity = body.get("original_severity", "unknown")
    user_id = req.headers.get("X-User-ID", "anonymous")

    if not prompt_text or not reason:
        return func.HttpResponse(json.dumps({"error": "prompt and reason are required"}), status_code=400, mimetype="application/json")

    valid_reasons = ["approved_use_case", "test_data", "client_authorized", "medical_necessity", "other"]
    if reason not in valid_reasons:
        return func.HttpResponse(json.dumps({"error": f"reason must be one of: {valid_reasons}"}), status_code=400, mimetype="application/json")

    if reason == "other" and not justification:
        return func.HttpResponse(json.dumps({"error": "justification required when reason is 'other'"}), status_code=400, mimetype="application/json")

    classification = {
        "action": f"OVERRIDE ({original_action})",
        "category": original_category,
        "severity": original_severity,
        "confidence": "user_override",
        "flagged_content": [],
        "summary": f"User overrode {original_action} decision. Reason: {reason}."
    }

    try:
        audit_blob = write_audit_log(prompt_text, classification, user_id, override=True, override_reason=reason, override_justification=justification)
    except Exception as e:
        logging.warning(f"Override audit failed: {e}")
        audit_blob = None

    override_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "original_action": original_action,
        "original_category": original_category,
        "original_severity": original_severity,
        "override_reason": reason,
        "override_justification": justification,
        "prompt_length": len(prompt_text),
        "prompt_preview": prompt_text[:100] + "..." if len(prompt_text) > 100 else prompt_text,
        "audit_ref": audit_blob
    }
    notify_manager(override_data)

    return func.HttpResponse(json.dumps({
        "status": "override_accepted",
        "reason": reason,
        "justification": justification,
        "audit_ref": audit_blob,
        "manager_notified": bool(os.environ.get("OVERRIDE_LOGIC_APP_URL"))
    }, indent=2), status_code=200, mimetype="application/json", headers={"Access-Control-Allow-Origin": "*"})


@app.route(route="audit-summary", methods=["GET", "OPTIONS"])
def audit_summary(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=200, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        })

    connection_string = os.environ.get("STORAGE_CONNECTION_STRING")
    container_name = os.environ.get("AUDIT_CONTAINER", "audit-logs")

    if not connection_string:
        return func.HttpResponse(json.dumps({"error": "Storage not configured"}), status_code=500, mimetype="application/json")

    try:
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container = blob_service.get_container_client(container_name)

        events = []
        for blob in container.list_blobs():
            blob_client = container.get_blob_client(blob.name)
            data = json.loads(blob_client.download_blob().readall().decode("utf-8"))
            data["blob_name"] = blob.name
            events.append(data)

        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Calculate summary
        total = len(events)
        allow = sum(1 for e in events if e.get("action") == "ALLOW")
        redact = sum(1 for e in events if e.get("action") == "REDACT")
        block = sum(1 for e in events if e.get("action") == "BLOCK")
        overrides = sum(1 for e in events if e.get("override"))

        # Category breakdown
        categories = {}
        for e in events:
            cat = e.get("category", "UNKNOWN")
            if e.get("action") != "ALLOW":
                categories[cat] = categories.get(cat, 0) + 1

        # Override reasons
        override_reasons = {}
        for e in events:
            if e.get("override") and e.get("override_reason"):
                r = e["override_reason"]
                override_reasons[r] = override_reasons.get(r, 0) + 1

        # Users with most blocks
        user_blocks = {}
        for e in events:
            if e.get("action") in ("BLOCK",) or e.get("override"):
                u = e.get("user_id", "anonymous")
                user_blocks[u] = user_blocks.get(u, 0) + 1

        summary = {
            "total": total,
            "allow": allow,
            "redact": redact,
            "block": block,
            "overrides": overrides,
            "categories": categories,
            "override_reasons": override_reasons,
            "user_blocks": user_blocks,
            "recent_events": events[:20]
        }

        return func.HttpResponse(
            json.dumps(summary, indent=2),
            status_code=200,
            mimetype="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        logging.error(f"Audit summary failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
