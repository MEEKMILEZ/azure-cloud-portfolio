"""
notifications.py
================
Sends real emails via Logic App + Outlook.com connector.

Flow:
  1. GPT 4o writes a human sounding email body
  2. Wrap it in a hospital styled HTML letterhead
  3. POST { to, subject, body_html } to the Logic App callback URL
  4. Logic App routes through Outlook.com connector to recipient's inbox
"""

import json
import logging
import os
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone
from openai import AzureOpenAI


# ============================================================
# GPT 4o PROMPT TEMPLATES
# ============================================================

PROMPT_BASE = """You write quick internal emails for the IT operations team at Lakeshore Regional
Health, a 250 bed community hospital. You are a senior IT coordinator. Your tone is
warm but brief, like someone who has 30 emails to write before lunch.

Hard rules for every email:
- No greeting filler. Skip "I hope this finds you well", "Hope you're doing well".
  Just say what happened.
- No corporate jargon. No "leveraging", "synergize", "best in class".
- Short paragraphs. 2 to 4 sentences each. Maximum 4 paragraphs total.
- Plain English. If a clinical staff member would not say it out loud, don't write it.
- Sign off as "IT Operations" or "Lakeshore IT", no specific name.
- Output the BODY ONLY. No subject line. No HTML tags. Plain text I can wrap.
"""

PROMPT_ONBOARD = PROMPT_BASE + """

Context:
- Recipient: {manager_name} (the new hire's manager)
- New hire: {user_name}
- Department: {department}
- Role: {role}
- Their accounts were provisioned automatically by the system today.

Mention naturally:
- They can sign in tomorrow morning. Temporary password sent through the secure
  HR portal.
- They need to set up multi factor authentication on day one.
- Plan for ~30 minutes of desk side time to get logged in and synced.

Write the email now. Body only.
"""

PROMPT_OFFBOARD = PROMPT_BASE + """

Context:
- Recipient: {manager_name} (the departing employee's manager)
- Departing employee: {user_name}
- Department: {department}
- Reason: {reason}
- Last working day: {last_day}
- Account disabled, sessions revoked, license reclaimed, mailbox converted to
  shared mailbox manager now has access to.

Mention naturally:
- Confirmation that access has been fully revoked as of today.
- Shared mailbox available for 90 days, then archived to compliance hold for
  7 years per HIPAA retention.
- OneDrive files: 30 days to request before deletion.

Write the email now. Body only.
"""

PROMPT_TRIAGE_URGENT = PROMPT_BASE + """

You are forwarding an incoming help desk ticket to the lead of the {assigned_team}
team. Brief them on what came in.

Ticket details:
- Submitter role: {submitter_role}
- Subject: {subject}
- Priority on this one: {priority}
- What's going on: {ai_summary}
- Recommended first step: {suggested_resolution}

What to write:
- One line stating the ticket has landed on their queue and the priority.
- Why it matters (the submitter's role and the impact on their work).
- The first step you'd suggest they try.

Write the email now. Body only.
"""

PROMPT_DRIFT_ALERT = PROMPT_BASE + """

You are sending the weekly access review summary to the compliance officer.

This week's numbers:
- Users with access they shouldn't have: {users_with_drift}
- Critical findings: {critical_findings}
- High findings: {high_findings}
- Most concerning case: {top_finding}
- Audit reference: {audit_ref}

What to write:
- Lead with the headline number.
- Call out the most concerning specific case in one sentence.
- Note that the full report is in Blob Storage at the audit reference.
- Confirm IT Ops is starting remediation today and will close out critical
  findings by end of business.

Write the email now. Body only.
"""

PROMPTS = {
    "onboard":        PROMPT_ONBOARD,
    "offboard":       PROMPT_OFFBOARD,
    "triage_urgent":  PROMPT_TRIAGE_URGENT,
    "drift_alert":    PROMPT_DRIFT_ALERT,
}

SUBJECTS = {
    "onboard":       "New hire access ready for {user_name}",
    "offboard":      "Access revoked for {user_name} effective {last_day}",
    "triage_urgent": "[{priority}] Ticket assigned to your team: {subject}",
    "drift_alert":   "Weekly drift scan: {critical_findings} critical, {high_findings} high",
}


def _openai_client():
    return AzureOpenAI(
        azure_endpoint=os.environ.get("OPENAI_ENDPOINT"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        api_version="2024-02-01"
    )


def _generate_body(notification_type, context):
    prompt_template = PROMPTS.get(notification_type)
    if not prompt_template:
        raise ValueError(f"Unknown notification_type: {notification_type}")
    prompt = prompt_template.format(**context)
    client = _openai_client()
    deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You write emails for the IT operations team at a hospital. Output the email body only, plaintext, no subject line."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()


def _plaintext_to_html(text):
    """Wrap plaintext in a clean Lakeshore Regional letterhead."""
    safe = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    paragraphs = [p.strip() for p in safe.split("\n\n") if p.strip()]
    body_html = "".join(f"<p style='margin:0 0 16px;line-height:1.55;color:#0b1f2a;'>{p}</p>" for p in paragraphs)
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f5f7fb;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f7fb;padding:24px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <tr><td style="background:#1f7374;padding:18px 28px;">
          <table cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="padding-right:12px;vertical-align:middle;">
                <div style="width:32px;height:32px;background:#ffffff;border-radius:6px;text-align:center;line-height:32px;color:#1f7374;font-weight:700;font-size:18px;">L</div>
              </td>
              <td style="vertical-align:middle;color:#ffffff;">
                <div style="font-size:15px;font-weight:600;line-height:1.2;">Lakeshore Regional Health</div>
                <div style="font-size:11px;opacity:0.85;letter-spacing:0.5px;text-transform:uppercase;">IT Operations</div>
              </td>
            </tr>
          </table>
        </td></tr>
        <tr><td style="padding:28px 28px 8px;font-size:14px;color:#0b1f2a;">{body_html}</td></tr>
        <tr><td style="background:#f8fafc;padding:14px 28px;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8;line-height:1.5;">
          Automated notification from the Lakeshore Regional IT Operations Console.
          Do not reply. For help, open a ticket at the IT intranet.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def send_notification(notification_type, recipient, context, audit_ref=None, importance="Normal"):
    override = os.environ.get("MANAGER_EMAIL_OVERRIDE", "").strip()
    actual_to = override if override else recipient
    if not actual_to:
        actual_to = "manager@lakeshore-health.local"

    logic_app_url = os.environ.get("LOGIC_APP_NOTIFY_URL", "").strip()

    try:
        subject = SUBJECTS[notification_type].format(**context)
    except (KeyError, ValueError) as e:
        subject = f"Lakeshore IT: {notification_type}"
        logging.warning(f"Subject format failed: {e}")

    body_text = None
    gen_error = None
    try:
        body_text = _generate_body(notification_type, context)
    except Exception as e:
        gen_error = f"GPT 4o body generation failed: {str(e)[:200]}"
        logging.error(gen_error)
        body_text = (
            f"This is a {notification_type} notification for {context.get('user_name', 'a user')}. "
            f"Audit reference: {audit_ref or 'unavailable'}."
        )

    body_html = _plaintext_to_html(body_text)
    preview = body_text[:140].replace("\n", " ").strip()
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    ts = datetime.now(timezone.utc).isoformat()

    if not logic_app_url:
        return {
            "sent": False,
            "to": actual_to,
            "subject": subject,
            "body_preview": preview,
            "body_full": body_text,
            "message_id": msg_id,
            "timestamp": ts,
            "error": "LOGIC_APP_NOTIFY_URL not configured"
        }

    payload = json.dumps({
        "to": actual_to,
        "subject": subject,
        "body_html": body_html
    }).encode("utf-8")

    req = urllib.request.Request(
        logic_app_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status = resp.status
            run_id = resp.headers.get("x-ms-workflow-run-id", "")
            return {
                "sent": True,
                "to": actual_to,
                "subject": subject,
                "body_preview": preview,
                "body_full": body_text,
                "message_id": msg_id,
                "run_id": run_id,
                "timestamp": ts,
                "logic_app_status": status,
                "error": gen_error
            }
    except urllib.error.HTTPError as e:
        return {
            "sent": False,
            "to": actual_to,
            "subject": subject,
            "body_preview": preview,
            "body_full": body_text,
            "message_id": msg_id,
            "timestamp": ts,
            "error": f"Logic App returned HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')[:200]}"
        }
    except Exception as e:
        return {
            "sent": False,
            "to": actual_to,
            "subject": subject,
            "body_preview": preview,
            "body_full": body_text,
            "message_id": msg_id,
            "timestamp": ts,
            "error": f"Logic App call failed: {str(e)[:200]}"
        }
