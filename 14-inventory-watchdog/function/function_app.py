"""
Project 14: Inventory Watchdog
Function App entry point. Two triggers share one pipeline:

  weekly_scan   timer, Mondays 11:00 UTC, the production schedule
  run_scan_http on demand trigger for demos and testing

Pipeline: read raw CSVs from bronze, validate and convert to Parquet
in silver, run the scan engine, write findings JSON to gold.

Authentication is the Function's managed identity end to end.
No storage keys, no API keys.
"""

import io
import json
import logging
import os
from datetime import date

import azure.functions as func
import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

from engine import run_scan
from narrator import narrate

APP_VERSION = "2026.06.13.3"

app = func.FunctionApp()

REQUIRED = {
    "item_master": ["sku_id", "description", "category", "uom",
                    "unit_cost", "supplier"],
    "lot_inventory": ["sku_id", "lot_number", "bin_location", "on_hand_qty",
                      "unit_cost", "received_date", "expiry_date"],
    "transactions": ["txn_id", "txn_date", "sku_id", "qty", "destination"],
}


def lake_client():
    endpoint = os.environ["LAKE_DFS_ENDPOINT"]
    return DataLakeServiceClient(
        account_url=endpoint, credential=DefaultAzureCredential())


def read_csv(client, filesystem, path):
    fs = client.get_file_system_client(filesystem)
    data = fs.get_file_client(path).download_file().readall()
    return pd.read_csv(io.BytesIO(data))


def write_bytes(client, filesystem, path, payload):
    fs = client.get_file_system_client(filesystem)
    f = fs.get_file_client(path)
    f.upload_data(payload, overwrite=True)


def validate(name, df):
    """Bronze to silver gate: required columns present, key fields
    populated, dates parseable. Bad rows are dropped and counted."""
    missing = [c for c in REQUIRED[name] if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")
    before = len(df)
    df = df.dropna(subset=REQUIRED[name])
    for col in ("txn_date", "received_date", "expiry_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            df = df.dropna(subset=[col])
    dropped = before - len(df)
    if dropped:
        logging.warning("%s: dropped %d invalid rows", name, dropped)
    return df


def execute_scan():
    today = date.today()
    client = lake_client()

    # Bronze to silver
    silver = {}
    for name in REQUIRED:
        raw = read_csv(client, "bronze", f"raw/{name}.csv")
        clean = validate(name, raw)
        buf = io.BytesIO()
        clean.to_parquet(buf, index=False)
        write_bytes(client, "silver", f"{name}.parquet", buf.getvalue())
        silver[name] = clean
        logging.info("silver/%s.parquet written, %d rows", name, len(clean))

    # Silver to gold
    findings = run_scan(
        silver["item_master"], silver["lot_inventory"],
        silver["transactions"], today)
    payload = json.dumps(findings, indent=2, default=str).encode("utf-8")
    out_path = f"findings/{today.isoformat()}/findings.json"
    write_bytes(client, "gold", out_path, payload)
    write_bytes(client, "gold", "findings/latest.json", payload)
    logging.info("gold/%s written", out_path)

    # Narration. The digest is what humans read; the JSON above is
    # the audit trail proving where every number came from.
    digest = narrate(findings)
    digest_bytes = digest.encode("utf-8")
    write_bytes(client, "gold",
                f"digest/{today.isoformat()}/digest.txt", digest_bytes)
    write_bytes(client, "gold", "digest/latest.txt", digest_bytes)
    logging.info("gold digest written, %d chars", len(digest))
    findings["digest"] = digest
    return findings


@app.timer_trigger(schedule="0 0 11 * * 1", arg_name="timer",
                   run_on_startup=False, use_monitor=False)
def weekly_scan(timer: func.TimerRequest) -> None:
    logging.info("Inventory Watchdog weekly scan starting")
    findings = execute_scan()
    logging.info("Scan complete: %s", json.dumps(findings["summary"]))


@app.route(route="run-scan", auth_level=func.AuthLevel.FUNCTION)
def run_scan_http(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Inventory Watchdog on demand scan starting")
    findings = execute_scan()
    body = {
        "code_version": APP_VERSION,
        "summary": findings["summary"],
        "digest_preview": findings["digest"][:200],
    }
    return func.HttpResponse(
        json.dumps(body, indent=2),
        mimetype="application/json", status_code=200)

@app.route(route="get-digest", auth_level=func.AuthLevel.FUNCTION)
def get_digest_http(req: func.HttpRequest) -> func.HttpResponse:
    """Returns the latest digest as plain text. The email workflow
    calls this instead of holding its own storage credentials."""
    client = lake_client()
    fs = client.get_file_system_client("gold")
    data = fs.get_file_client("digest/latest.txt").download_file().readall()
    return func.HttpResponse(data, mimetype="text/plain", status_code=200)
