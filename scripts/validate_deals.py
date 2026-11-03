"""Validate manually verified deal offers before publication; stdlib only."""
import datetime as dt
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

FEED = Path(__file__).resolve().parents[1] / "site" / "deals.json"
REQUIRED = ("id", "title", "merchant", "url", "price_chf", "verified_at", "status")
def validate(feed):
    errors=[]
    offers=feed.get("offers", [])
    if not isinstance(offers, list): return ["offers must be a list"]
    seen=set()
    for n,offer in enumerate(offers, 1):
        prefix=f"offer[{n}]"
        if not isinstance(offer, dict): errors.append(f"{prefix} must be object");continue
        for field in REQUIRED:
            if field not in offer or offer[field] in ("",None):
                errors.append(f"{prefix} missing {field}")
        key=offer.get("id")
        if key in seen: errors.append(f"{prefix} duplicate ID")
        seen.add(key)
        if offer.get("status") not in ("verified","draft","expired"):
            errors.append(f"{prefix} invalid status")
        if offer.get("status") == "verified":
            u=urlparse(str(offer.get("url","")))
            if u.scheme!="https" or not u.hostname: errors.append(f"{prefix} must have valid HTTPS URL")
            if not isinstance(offer.get("price_chf"),(int,float)) or isinstance(offer.get("price_chf"),bool) or offer["price_chf"]<=0:
                errors.append(f"{prefix} price_chf must be positive number")
            for k in ("shipping_chf",):
                if k in offer and (not isinstance(offer[k],(int,float)) or offer[k]<0):
                    errors.append(f"{prefix} invalid {k}")
            for field in ("verified_at","valid_until"):
                if offer.get(field):
                    try: dt.datetime.fromisoformat(offer[field].replace("Z","+00:00"))
                    except (TypeError,ValueError): errors.append(f"{prefix} invalid {field}")
            if not offer.get("evidence_url"):
                errors.append(f"{prefix} requires evidence_url; don't publish unverified claims")
    return errors

if __name__=="__main__":
    data=json.loads(FEED.read_text(encoding="utf-8"))
    err=validate(data)
    if err:
        print("\n".join(err), file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: {len(data.get('offers',[]))} offers, all validated")
