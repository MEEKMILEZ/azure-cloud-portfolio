"""
Project 14: Inventory Watchdog
Scan engine. Pure computation, no Azure dependencies, so this module
is unit testable on any machine against the seed 14 data.

Methodology, all industry standard:
  FSN classification   turnover ratio over 3 is Fast, 1 to 3 Slow,
                       below 1 Non moving
  Aging buckets        days since last pick: 0-30, 31-60, 61-90, 90+
  Carrying cost        25 percent of inventory value per year, the
                       midpoint of the accepted 20 to 30 percent range
  Expiry runway        at the trailing 90 day burn rate, how much of
                       each lot cannot sell before its expiry date

The AI never touches these numbers. Code calculates, AI communicates.
"""

from datetime import date, timedelta

import pandas as pd

CARRYING_COST_RATE = 0.25
FSN_FAST_MIN_TURNS = 3.0
FSN_SLOW_MIN_TURNS = 1.0
EXPIRY_HORIZON_DAYS = 180
NON_MOVER_DAYS = 90
DECLINE_RATIO = 0.5


def aging_bucket(days):
    if days <= 30:
        return "0-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    return "90+"


def run_scan(items, lots, txns, today):
    """Compute watchdog findings. Returns a dict ready for JSON."""
    txns = txns.copy()
    txns["txn_date"] = pd.to_datetime(txns["txn_date"]).dt.date
    lots = lots.copy()
    lots["expiry_date"] = pd.to_datetime(lots["expiry_date"]).dt.date

    year_ago = today - timedelta(days=365)
    d90 = today - timedelta(days=90)
    d30 = today - timedelta(days=30)

    annual = txns[txns["txn_date"] >= year_ago].groupby("sku_id")["qty"].sum()
    last_pick = txns.groupby("sku_id")["txn_date"].max()
    qty_90 = txns[txns["txn_date"] >= d90].groupby("sku_id")["qty"].sum()
    qty_30 = txns[txns["txn_date"] >= d30].groupby("sku_id")["qty"].sum()

    on_hand = lots.groupby("sku_id")["on_hand_qty"].sum()
    lots["line_value"] = lots["on_hand_qty"] * lots["unit_cost"]
    value = lots.groupby("sku_id")["line_value"].sum()

    sku_rows = []
    for _, item in items.iterrows():
        sku = item["sku_id"]
        oh = int(on_hand.get(sku, 0))
        val = float(value.get(sku, 0.0))
        ann = int(annual.get(sku, 0))
        burn90 = float(qty_90.get(sku, 0)) / 90.0
        burn30 = float(qty_30.get(sku, 0)) / 30.0

        turnover = (ann / oh) if oh > 0 else None
        if turnover is None or turnover < FSN_SLOW_MIN_TURNS:
            fsn = "N"
        elif turnover < FSN_FAST_MIN_TURNS:
            fsn = "S"
        else:
            fsn = "F"

        lp = last_pick.get(sku)
        days_since = (today - lp).days if lp is not None else 9999

        declining = burn90 > 0 and burn30 < DECLINE_RATIO * burn90

        sku_rows.append({
            "sku_id": sku,
            "description": item["description"],
            "category": item["category"],
            "on_hand_qty": oh,
            "on_hand_value": round(val, 2),
            "annual_qty": ann,
            "turnover": round(turnover, 2) if turnover is not None else None,
            "fsn_class": fsn,
            "days_since_last_pick": days_since,
            "aging_bucket": aging_bucket(days_since),
            "burn_rate_90d": round(burn90, 3),
            "burn_rate_30d": round(burn30, 3),
            "declining": bool(declining),
            "carrying_cost_annual": round(val * CARRYING_COST_RATE, 2),
        })
    sku_df = pd.DataFrame(sku_rows).set_index("sku_id", drop=False)

    # Expiry runway per lot. Unsellable portion is the stock that the
    # trailing burn rate cannot consume before the expiry date.
    expiry_findings = []
    for _, lot in lots.iterrows():
        sku = lot["sku_id"]
        burn = float(sku_df.loc[sku, "burn_rate_90d"])
        days_to_expiry = (lot["expiry_date"] - today).days
        if days_to_expiry > EXPIRY_HORIZON_DAYS:
            continue
        sellable = burn * max(days_to_expiry, 0)
        unsellable = max(lot["on_hand_qty"] - sellable, 0)
        if unsellable <= 0:
            continue
        risk_value = unsellable * lot["unit_cost"]
        expiry_findings.append({
            "sku_id": sku,
            "description": sku_df.loc[sku, "description"],
            "lot_number": lot["lot_number"],
            "bin_location": lot["bin_location"],
            "on_hand_qty": int(lot["on_hand_qty"]),
            "days_to_expiry": int(days_to_expiry),
            "expiry_date": lot["expiry_date"].isoformat(),
            "projected_writeoff_qty": int(round(unsellable)),
            "projected_writeoff_value": round(float(risk_value), 2),
            "severity": "CRITICAL",
            "recommendation": (
                "Initiate vendor return or transfer now. At the current "
                "burn rate this lot cannot sell through before expiry."
            ),
        })
    expiry_findings.sort(key=lambda r: -r["projected_writeoff_value"])

    non_movers = []
    for _, r in sku_df.iterrows():
        if r["fsn_class"] == "N" and r["days_since_last_pick"] > NON_MOVER_DAYS:
            non_movers.append({
                "sku_id": r["sku_id"],
                "description": r["description"],
                "on_hand_qty": int(r["on_hand_qty"]),
                "on_hand_value": float(r["on_hand_value"]),
                "days_since_last_pick": int(r["days_since_last_pick"]),
                "carrying_cost_annual": float(r["carrying_cost_annual"]),
                "severity": "WARNING",
                "recommendation": (
                    "Halt reorders. Evaluate transfer, vendor return, "
                    "or liquidation."
                ),
            })
    non_movers.sort(key=lambda r: -r["on_hand_value"])

    decliners = []
    for _, r in sku_df.iterrows():
        if r["declining"] and r["fsn_class"] != "N":
            decliners.append({
                "sku_id": r["sku_id"],
                "description": r["description"],
                "burn_rate_90d": float(r["burn_rate_90d"]),
                "burn_rate_30d": float(r["burn_rate_30d"]),
                "on_hand_value": float(r["on_hand_value"]),
                "severity": "INFO",
                "recommendation": (
                    "Demand trending down. Review reorder quantity "
                    "before the next purchase cycle."
                ),
            })
    decliners.sort(key=lambda r: -r["on_hand_value"])

    dead_value = sum(r["on_hand_value"] for r in non_movers)
    summary = {
        "scan_date": today.isoformat(),
        "company": "Northbridge Medical Supply",
        "total_skus": int(len(sku_df)),
        "total_inventory_value": round(float(sku_df["on_hand_value"].sum()), 2),
        "fsn_counts": sku_df["fsn_class"].value_counts().to_dict(),
        "critical_count": len(expiry_findings),
        "warning_count": len(non_movers),
        "info_count": len(decliners),
        "projected_expiry_writeoff_value": round(
            sum(r["projected_writeoff_value"] for r in expiry_findings), 2),
        "dead_stock_value": round(dead_value, 2),
        "dead_stock_carrying_cost_weekly": round(
            dead_value * CARRYING_COST_RATE / 52.0, 2),
    }

    return {
        "summary": summary,
        "critical_expiry_risks": expiry_findings,
        "warning_non_movers": non_movers,
        "info_declining": decliners,
        "sku_detail": sku_df.drop(columns=["sku_id"]).reset_index().to_dict("records"),
    }
