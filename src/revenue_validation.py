"""Fail-closed revenue validation audit. No inferred commissions from views or clicks.

Usage: python -m src.revenue_validation --deals site/deals.json
Optional: --click-db /persistent/dealradar_events.sqlite
          --commissions /private/confirmed_commissions.json
Commission file schema: {"transactions":[{"transaction_id":"...", "status":"confirmed",
"commission_chf":2.5, "offer_id":"..."}]}.
Only independently reconciled confirmed transactions may be supplied here.
"""
import argparse
import json
import sqlite3
from pathlib import Path

def audit(deals_path, click_db=None, commissions=None):
    deals = json.loads(Path(deals_path).read_text(encoding="utf-8"))
    verified = [x for x in deals.get("offers", []) if
                x.get("status") == "verified" and x.get("title") and
                x.get("url", "").startswith("https://") and
                isinstance(x.get("price_chf"), (int, float)) and
                not isinstance(x.get("price_chf"), bool) and
                x["price_chf"] >= 0 and x.get("verified_at")]
    result = {"status": "NOT_VALIDATED", "verified_offers": len(verified),
              "tracked_clicks": None, "confirmed_sales": None,
              "confirmed_commission_chf": None, "revenue_verified": False,
              "blockers": []}
    if not verified:
        result["blockers"].append("NO_VERIFIED_OFFERS")
    if click_db is None or not Path(click_db).is_file():
        result["blockers"].append("CLICK_DATABASE_NOT_AVAILABLE")
    else:
        try:
            with sqlite3.connect(f"file:{Path(click_db).resolve()}?mode=ro", uri=True) as db:
                result["tracked_clicks"] = db.execute("SELECT count(*) FROM click_events").fetchone()[0]
        except sqlite3.Error:
            result["blockers"].append("CLICK_DATABASE_UNREADABLE")
    if commissions is None or not Path(commissions).is_file():
        result["blockers"].append("CONFIRMED_COMMISSIONS_NOT_AVAILABLE")
    else:
        try:
            transactions = json.loads(Path(commissions).read_text(encoding="utf-8"))["transactions"]
            if not isinstance(transactions, list):
                raise ValueError("transactions must be list")
            seen = set()
            total = 0.0
            count = 0
            for t in transactions:
                tid = t["transaction_id"]
                amount = t["commission_chf"]
                if not isinstance(tid, str) or not tid or tid in seen:
                    raise ValueError("duplicate or invalid transaction")
                seen.add(tid)
                if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
                    raise ValueError("invalid commission")
                if t["status"] == "confirmed":
                    total += amount
                    count += 1
            result["confirmed_sales"] = count
            result["confirmed_commission_chf"] = round(total, 2)
            result["revenue_verified"] = True
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            result["blockers"].append("COMMISSIONS_INVALID")
    if not result["blockers"]:
        result["status"] = "MEASUREMENT_READY"
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--deals", default="site/deals.json")
    p.add_argument("--click-db")
    p.add_argument("--commissions")
    a = p.parse_args()
    print(json.dumps(audit(a.deals, a.click_db, a.commissions), sort_keys=True))

if __name__ == "__main__":
    main()
