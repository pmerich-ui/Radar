"""Adapter for supplied DealRadar price-chart renderer.

The vendor renderer is deliberately not bundled here until its source is
committed. Import this adapter only when the original render_price_video.py
has been added to src/price_video.py. No live price claims from demo data.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from .pipeline import ninety_day_median

def validate_price_payload(deal: dict, *, demo: bool = False) -> dict:
    if not demo:
        raise ValueError("Live rendering disabled until deal source verification is connected")
    if not str(deal.get("id","")).startswith("demo-"):
        raise ValueError("Demo mode requires demo-prefixed ID")
    if deal.get("currency") != "CHF":
        raise ValueError("Only CHF is supported")
    rows = deal.get("history", [])
    if len(rows) < 10:
        raise ValueError("At least ten dated price observations required")
    if any(not isinstance(row,(list,tuple)) or len(row)!=2 for row in rows):
        raise ValueError("Invalid history row")
    observations = [{"at":str(ts)+"T00:00:00+00:00" if len(str(ts))==10 else str(ts),"price_chf":price} for ts,price in rows]
    med = ninety_day_median(observations,datetime.now(timezone.utc))
    if med is None:
        raise ValueError("Insufficient valid observations in last 90 days")
    return {"median_90d_chf":med,"observations":len(observations),"demo":True}

def render_demo(deal_path: str, output_path: str) -> dict:
    from .price_video import render, validate
    deal=json.loads(Path(deal_path).read_text(encoding="utf-8"))
    proof=validate_price_payload(deal,demo=True)
    result=render(deal,output_path,variant="A")
    qa=validate(output_path)
    if not qa["ok"]:
        raise RuntimeError("MP4 QA failed: "+", ".join(qa["errors"]))
    return {**result,"qa":qa,"price_proof":proof,"publication":"DISABLED_DEMO"}
