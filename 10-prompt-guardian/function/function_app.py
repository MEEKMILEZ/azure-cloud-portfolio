import azure.functions as func
import json
import logging
import os
import hashlib
from datetime import datetime, timezone
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient, BlobBlock
import uuid

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
    endpoint = os.environ.get("OPENAI_ENDPOINT")
    api_key  = os.environ.get("OPENAI_API_KEY")
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-02-01"
    )


def classify_prompt(prompt_text: str) -> dict:
    client     = get_openai_client()
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

    text   = response.choices[0].message.content
    text   = text.replace("```json", "").replace("```", "").strip()
    result = json.loads(text)
    return result


def write_audit_log(prompt_text: str, classification: dict, user_id: str = "anonymous"):
    connection_string = os.environ.get("STORAGE_CONNECTION_STRING")
    container_name    = os.environ.get("AUDIT_CONTAINER", "audit-logs")

    if not connection_string:
        logging.warning("No storage connection string — skipping audit log")
        return

    blob_client = BlobServiceClient.from_connection_string(connection_string)
    container   = blob_client.get_container_client(container_name)

    timestamp  = datetime.now(timezone.utc)
    date_str   = timestamp.strftime("%Y/%m/%d")
    blob_name  = f"{date_str}/audit-{timestamp.strftime('%H%M%S')}-{uuid.uuid4().hex[:8]}.json"

    # Store hash of prompt, never raw content
    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()

    audit_entry = {
        "timestamp":       timestamp.isoformat(),
        "user_id":         user_id,
        "prompt_hash":     prompt_hash,
        "prompt_length":   len(prompt_text),
        "action":          classification.get("action"),
        "category":        classification.get("category"),
        "severity":        classification.get("severity"),
        "confidence":      classification.get("confidence"),
        "flagged_content": classification.get("flagged_content", []),
        "summary":         classification.get("summary"),
        "override":        False,
        "override_reason": None
    }

    container.upload_blob(
        name=blob_name,
        data=json.dumps(audit_entry, indent=2),
        overwrite=False
    )
    logging.info(f"Audit log written: {blob_name}")
    return blob_name


@app.route(route="classify", methods=["POST", "OPTIONS"])
def classify(req: func.HttpRequest) -> func.HttpResponse:

    # Handle CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin":  "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, X-User-ID"
            }
        )

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json"
        )

    prompt_text = body.get("prompt", "").strip()
    user_id     = req.headers.get("X-User-ID", "anonymous")

    if not prompt_text:
        return func.HttpResponse(
            json.dumps({"error": "prompt field is required"}),
            status_code=400,
            mimetype="application/json"
        )

    if len(prompt_text) > 10000:
        return func.HttpResponse(
            json.dumps({"error": "prompt exceeds 10,000 character limit"}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        classification = classify_prompt(prompt_text)
    except json.JSONDecodeError as e:
        logging.error(f"OpenAI returned invalid JSON: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Classification engine returned invalid response"}),
            status_code=500,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Classification failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Classification failed: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

    try:
        audit_blob = write_audit_log(prompt_text, classification, user_id)
        classification["audit_ref"] = audit_blob
    except Exception as e:
        logging.warning(f"Audit log failed (non-fatal): {e}")
        classification["audit_ref"] = None

    return func.HttpResponse(
        json.dumps(classification, indent=2),
        status_code=200,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"}
    )
