"""Read-only audit for Awin CSV.GZ exports. Never publishes deals."""
import argparse
import collections
import csv
import gzip
import json
from pathlib import Path
from urllib.parse import urlparse

def audit(path):
    counts = collections.Counter()
    currencies = collections.Counter()
    missing = collections.Counter()
    seen = set()
    duplicates = invalid = total = 0
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            total += 1
            merchant = row.get("merchant_id", "")
            counts[(merchant, row.get("merchant_name", ""))] += 1
            currencies[row.get("currency", "")] += 1
            for field in ("last_updated", "delivery_cost", "product_name", "search_price", "aw_deep_link"):
                if not row.get(field):
                    missing[field] += 1
            key = (merchant, row.get("merchant_product_id", ""))
            duplicates += key in seen
            seen.add(key)
            try:
                price = float(row.get("search_price", ""))
            except (ValueError, TypeError):
                price = 0
            link = urlparse(row.get("aw_deep_link", ""))
            if price <= 0 or not row.get("product_name") or link.scheme != "https" or link.hostname not in ("awin1.com", "www.awin1.com"):
                invalid += 1
    return {
        "total_rows": total,
        "merchants": [{"merchant_id": mid, "merchant": name, "rows": n} for (mid, name), n in counts.most_common()],
        "currencies": dict(currencies),
        "missing_fields": dict(missing),
        "duplicate_merchant_product_ids": duplicates,
        "invalid_rows": invalid,
        "publishable_deals": 0,
        "publishing_enabled": False,
        "warning": "Feed price is not independent proof of a deal; merchant approval, Swiss delivery and price history require verification."
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("feed")
    parser.add_argument("--out", default="feed_audit.json")
    args = parser.parse_args()
    result = audit(args.feed)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
