"""
Project 14: Inventory Watchdog
Narration layer. Sends computed findings to the deployed model and
returns a plain text weekly digest. The model never calculates,
it only explains numbers already computed by engine.py.

Auth is the Function's managed identity. No API keys.
"""

import json
import os

import requests
from azure.identity import DefaultAzureCredential

API_VERSION = "2024-12-01-preview"

PROMPT = """You are drafting the weekly inventory review memo for the \
operations leadership team at Northbridge Medical Supply, a medical \
products distributor. Below are this week's computed findings from the \
inventory scan in JSON.

Write a concise memo in plain business English with these sections:
1. One short paragraph: total dollars at risk and the overall picture.
2. Urgent this week: the expiry risk lots, largest dollar value first, \
with the recommended action for each.
3. Dead stock: the non moving items, what they cost us weekly to hold, \
and the recommended next step.
4. Watch list: items with declining demand.
5. A closing line with the three actions to take before next Monday.

Rules: use only the numbers provided, never invent or recalculate \
figures. Never use em dashes, en dashes, hyphens as separators, or \
parentheses anywhere. Use commas, colons, and periods instead. Round dollars to whole numbers with thousands separators. \
Refer to items by SKU and short description. Plain text only, no \
markdown symbols. Keep it under 450 words. Write as a human operations \
analyst signing off as Inventory Watchdog.

FINDINGS JSON:
"""


def narrate(findings):
    endpoint = os.environ["OPENAI_ENDPOINT"].rstrip("/")
    deployment = os.environ["OPENAI_DEPLOYMENT_NAME"]

    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")

    compact = {
        "summary": findings["summary"],
        "critical_expiry_risks": findings["critical_expiry_risks"],
        "warning_non_movers": findings["warning_non_movers"],
        "info_declining": findings["info_declining"],
    }

    url = (f"{endpoint}/openai/deployments/{deployment}"
           f"/chat/completions?api-version={API_VERSION}")
    body = {
        "messages": [
            {"role": "user",
             "content": PROMPT + json.dumps(compact, default=str)}
        ],
        "max_completion_tokens": 2000,
    }
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token.token}",
                 "Content-Type": "application/json"},
        json=body, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
