#!/usr/bin/env python3
"""DealRadar 24h analytics ledger. Standard-library SQLite; no external calls.
Claim once per public video and checkpoint, only after >=24h. No fabricated metrics.
"""
import json, sqlite3, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

METRICS=("TKPO02","TKPO03","TKPO06","TKPO07","TKPO08","TKPO09","TKPO10","TKPO11","TKPO13","TKPO15")
def parse_time(value):
    if not isinstance(value,str): raise ValueError("timestamp_required")
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None: raise ValueError("timezone_required")
    return dt.astimezone(timezone.utc)

def record(db_path, video_id, published_at, observed_at, metrics):
    if not isinstance(video_id,str) or not video_id.strip(): raise ValueError("video_id_required")
    pub,obs=parse_time(published_at),parse_time(observed_at)
    if obs < pub+timedelta(hours=24): return {"status":"NOT_DUE","video_id":video_id}
    if not isinstance(metrics,dict): raise ValueError("metrics_object_required")
    values={key:metrics.get(key) for key in METRICS}
    available={k:v for k,v in values.items() if v is not None}
    if not available: return {"status":"DATA_UNAVAILABLE","video_id":video_id}
    p=Path(db_path);p.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(p,timeout=20) as con:
        con.execute("PRAGMA busy_timeout=20000")
        con.execute("""CREATE TABLE IF NOT EXISTS analytics_24h (
          video_id TEXT PRIMARY KEY, published_at TEXT NOT NULL,
          observed_at TEXT NOT NULL, payload TEXT NOT NULL)""")
        cur=con.execute("INSERT OR IGNORE INTO analytics_24h VALUES (?,?,?,?)",
                        (video_id,pub.isoformat(),obs.isoformat(),json.dumps(values,ensure_ascii=False)))
        if cur.rowcount==0: return {"status":"ALREADY_RECORDED","video_id":video_id}
    return {"status":"RECORDED","video_id":video_id,"metrics":values,
            "missing":[k for k,v in values.items() if v is None],
            "assessment":"DATEN UNZUREICHEND",
            "note":"Snapshot after >=24h, not necessarily exactly at hour 24. Compare with channel median separately."}

if __name__=="__main__":
    if len(sys.argv)!=3:
        print("Usage: analytics_24h.py ledger.sqlite input.json",file=sys.stderr);sys.exit(2)
    data=json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    result=record(sys.argv[1],data["video_id"],data["published_at"],data["observed_at"],data.get("metrics",{}))
    print(json.dumps(result,ensure_ascii=False,indent=2))
