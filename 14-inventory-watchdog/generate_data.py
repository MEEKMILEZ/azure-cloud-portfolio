"""
Project 14: Inventory Watchdog
Phase 2: Synthetic data generator for Northbridge Medical Supply

Generates three WMS style extracts for a fictional medical distributor:
  bronze/item_master.csv      one row per SKU
  bronze/lot_inventory.csv    one row per lot on hand, with expiry dates
  bronze/transactions.csv     12 months of daily pick history

All data is synthetic. Northbridge Medical Supply and every hospital
named here are fictional. A fixed random seed makes every run
reproducible, so the watchdog findings in the README always match
what anyone gets by rerunning this script.

Planted problems for the watchdog to catch:
  DEAD skus        no picks for 150 to 330 days, overstocked
  DECLINING skus   demand fading toward zero in the last 90 days
  EXPIRY TRAP lots slow burn rate with a lot that expires before
                   the stock can possibly sell through

Usage:
  python generate_data.py
Outputs land in a local data/bronze folder, ready for upload.
"""

import csv
import os
import random
from datetime import date, timedelta

import numpy as np

SEED = 14
random.seed(SEED)
np.random.seed(SEED)

TODAY = date(2026, 6, 12)
HISTORY_DAYS = 365
OUT_DIR = os.path.join("data", "bronze")

NUM_FAST = 60
NUM_MEDIUM = 120
NUM_SLOW = 85
NUM_DECLINING = 15
NUM_DEAD = 20
NUM_EXPIRY_TRAP = 12  # drawn from the slow group

CATEGORIES = {
    "Exam Gloves":          {"cost": (4.5, 12.0),   "uom": "BX"},
    "Syringes and Needles": {"cost": (8.0, 30.0),   "uom": "BX"},
    "Wound Care":           {"cost": (6.0, 45.0),   "uom": "CS"},
    "IV Therapy":           {"cost": (15.0, 80.0),  "uom": "CS"},
    "Sutures":              {"cost": (40.0, 160.0), "uom": "BX"},
    "Surgical Instruments": {"cost": (60.0, 450.0), "uom": "EA"},
    "PPE and Apparel":      {"cost": (10.0, 55.0),  "uom": "CS"},
    "Diagnostics":          {"cost": (25.0, 220.0), "uom": "KT"},
}

SUPPLIERS = [
    "Helix Medical Manufacturing", "TrueNorth Surgical", "Beaumont Devices",
    "ClearPath Diagnostics", "Sterling Medical Products",
]

HOSPITALS = [
    "Lakecrest General Hospital", "Birchwood Community Health Centre",
    "Stonegate Surgical Centre", "Harbourview Regional Hospital",
    "Fairfield Family Clinic Network",
]

# Weekday demand factors, Monday through Sunday. Hospitals order
# heavily early week and barely on weekends.
WEEKDAY_FACTOR = [1.25, 1.20, 1.10, 1.00, 0.90, 0.30, 0.25]

ZONES = ["A", "B", "C", "D"]


def make_skus():
    skus = []
    profiles = (
        ["FAST"] * NUM_FAST + ["MEDIUM"] * NUM_MEDIUM + ["SLOW"] * NUM_SLOW
        + ["DECLINING"] * NUM_DECLINING + ["DEAD"] * NUM_DEAD
    )
    random.shuffle(profiles)
    cat_names = list(CATEGORIES.keys())
    for i, profile in enumerate(profiles, start=1):
        cat = random.choice(cat_names)
        lo, hi = CATEGORIES[cat]["cost"]
        if profile == "FAST":
            base = random.uniform(8, 40)
        elif profile == "MEDIUM":
            base = random.uniform(2, 8)
        elif profile in ("SLOW", "DECLINING"):
            base = random.uniform(0.2, 2.0)
        else:  # DEAD
            base = random.uniform(0.3, 1.5)
        skus.append({
            "sku_id": f"NMS-{i:04d}",
            "description": f"{cat} item {i:04d}",
            "category": cat,
            "uom": CATEGORIES[cat]["uom"],
            "unit_cost": round(random.uniform(lo, hi), 2),
            "supplier": random.choice(SUPPLIERS),
            "profile": profile,
            "base_demand": base,
            "dead_after": (
                TODAY - timedelta(days=random.randint(150, 330))
                if profile == "DEAD" else None
            ),
        })
    # Mark expiry traps among slow movers
    slow_ids = [s for s in skus if s["profile"] == "SLOW"]
    for s in random.sample(slow_ids, NUM_EXPIRY_TRAP):
        s["expiry_trap"] = True
    return skus


def daily_qty(sku, day):
    """Poisson draw for one sku on one calendar day."""
    base = sku["base_demand"]
    if sku["profile"] == "DEAD" and day >= sku["dead_after"]:
        return 0
    if sku["profile"] == "DECLINING":
        days_left = (TODAY - day).days
        if days_left < 90:
            base = base * max(days_left, 0) / 90.0  # fade to zero
    lam = base * WEEKDAY_FACTOR[day.weekday()]
    return int(np.random.poisson(lam))


def make_transactions(skus):
    rows = []
    txn = 0
    start = TODAY - timedelta(days=HISTORY_DAYS)
    for d in range(HISTORY_DAYS):
        day = start + timedelta(days=d)
        for sku in skus:
            qty = daily_qty(sku, day)
            if qty > 0:
                txn += 1
                rows.append({
                    "txn_id": f"T{txn:07d}",
                    "txn_date": day.isoformat(),
                    "sku_id": sku["sku_id"],
                    "qty": qty,
                    "destination": random.choice(HOSPITALS),
                })
    return rows


def recent_daily_burn(sku, txns_by_sku):
    """Average units per day over the last 90 days."""
    cutoff = TODAY - timedelta(days=90)
    total = sum(
        t["qty"] for t in txns_by_sku.get(sku["sku_id"], [])
        if date.fromisoformat(t["txn_date"]) >= cutoff
    )
    return total / 90.0


def make_lots(skus, txns):
    txns_by_sku = {}
    for t in txns:
        txns_by_sku.setdefault(t["sku_id"], []).append(t)

    rows = []
    lot_n = 0
    for sku in skus:
        burn = recent_daily_burn(sku, txns_by_sku)
        profile = sku["profile"]

        if profile == "DEAD":
            on_hand = int(sku["base_demand"] * random.uniform(120, 250))
            on_hand = max(on_hand, 40)
        elif sku.get("expiry_trap"):
            on_hand = int(max(burn, 0.1) * random.uniform(300, 500))
            on_hand = max(on_hand, 60)
        elif profile in ("SLOW", "DECLINING"):
            on_hand = int(max(burn, 0.1) * random.uniform(45, 90))
        else:
            on_hand = int(max(burn, 1.0) * random.uniform(15, 35))
        on_hand = max(on_hand, 5)

        n_lots = 1 if profile in ("DEAD", "SLOW", "DECLINING") else random.randint(1, 3)
        split = np.random.dirichlet([2.0] * n_lots)
        for share in split:
            lot_n += 1
            qty = max(int(on_hand * share), 1)
            received = TODAY - timedelta(days=random.randint(20, 400))
            if sku.get("expiry_trap"):
                expiry = TODAY + timedelta(days=random.randint(60, 180))
            elif profile == "DEAD":
                expiry = TODAY + timedelta(days=random.randint(120, 720))
            else:
                expiry = TODAY + timedelta(days=random.randint(365, 1095))
            rows.append({
                "sku_id": sku["sku_id"],
                "lot_number": f"L{lot_n:06d}",
                "bin_location": f"{random.choice(ZONES)}-{random.randint(1,40):02d}-{random.randint(1,6)}",
                "on_hand_qty": qty,
                "unit_cost": sku["unit_cost"],
                "received_date": received.isoformat(),
                "expiry_date": expiry.isoformat(),
            })
    return rows


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    skus = make_skus()
    txns = make_transactions(skus)
    lots = make_lots(skus, txns)

    item_fields = ["sku_id", "description", "category", "uom",
                   "unit_cost", "supplier"]
    items = [{k: s[k] for k in item_fields} for s in skus]

    write_csv(os.path.join(OUT_DIR, "item_master.csv"), items, item_fields)
    write_csv(os.path.join(OUT_DIR, "lot_inventory.csv"), lots,
              ["sku_id", "lot_number", "bin_location", "on_hand_qty",
               "unit_cost", "received_date", "expiry_date"])
    write_csv(os.path.join(OUT_DIR, "transactions.csv"), txns,
              ["txn_id", "txn_date", "sku_id", "qty", "destination"])

    inv_value = sum(r["on_hand_qty"] * r["unit_cost"] for r in lots)
    dead_value = sum(
        r["on_hand_qty"] * r["unit_cost"] for r in lots
        if next(s for s in skus if s["sku_id"] == r["sku_id"])["profile"] == "DEAD"
    )
    trap_value = sum(
        r["on_hand_qty"] * r["unit_cost"] for r in lots
        if next(s for s in skus if s["sku_id"] == r["sku_id"]).get("expiry_trap")
    )
    print(f"SKUs: {len(items)}  Lots: {len(lots)}  Transactions: {len(txns)}")
    print(f"Total inventory value: ${inv_value:,.2f}")
    print(f"Planted dead stock value: ${dead_value:,.2f} across {NUM_DEAD} SKUs")
    print(f"Planted expiry trap value: ${trap_value:,.2f} across {NUM_EXPIRY_TRAP} SKUs")
    print(f"Files written to {OUT_DIR}")


if __name__ == "__main__":
    main()
