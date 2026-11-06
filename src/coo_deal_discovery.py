"""COO deal discovery: read-only inventory, conservative candidate ranking.

Existing offers are candidates, not approved merchants or verified bargains.
No internet scraping, purchases, publication, or fabricated price history.
"""
import csv
import gzip
import json
from pathlib import Path

def scan(root, limit=20):
    root = Path(root)
    sources = sorted((root / "data/awin/incoming").glob("*.csv.gz"))
    candidates = []
    total = 0
    for source in sources:
        with gzip.open(source, "rt", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                total += 1
                if row.get("currency", "").upper() != "CHF":
                    continue
                try:
                    price = float(row.get("search_price", ""))
                except (ValueError, TypeError):
                    continue
                if price <= 0 or not row.get("product_name") or not row.get("merchant_name"):
                    continue
                link = row.get("aw_deep_link", "")
                if not link.startswith("https://"):
                    continue
                candidates.append({
                    "product_name": row["product_name"][:160],
                    "merchant_name": row["merchant_name"][:100],
                    "price_chf": price,
                    "product_url": link,
                    "merchant_id": row.get("merchant_id", ""),
                    "product_id": row.get("merchant_product_id", ""),
                    "status": "CANDIDATE_UNVERIFIED",
                    "merchant_approved": None,
                    "swiss_delivery_verified": None,
                    "discount_verified": None,
                    "image_rights_verified": None
                })
                if len(candidates) >= limit:
                    break
        if len(candidates) >= limit:
            break
    return {"status": "CANDIDATES_FOUND" if candidates else "NO_VERIFIED_FEED_CANDIDATES",
            "feed_files": len(sources), "rows_scanned": total,
            "candidates": candidates, "publishable_deals": 0,
            "next_action": "Verify merchant approval, Swiss delivery, real checkout price and media rights before advertising."}

def main():
    root = Path(__file__).resolve().parents[1]
    result = scan(root)
    output = root / "reports/deal_candidates.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "candidates": len(result["candidates"]),
                      "publishable_deals": 0, "feed_files": result["feed_files"]}))

if __name__ == "__main__":
    main()
