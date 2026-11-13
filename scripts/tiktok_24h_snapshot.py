#!/usr/bin/env python3
"""Fail-closed, idempotent TikTok 24h snapshot evaluator. Standard library only.

Input JSON: {"now":"2026-11-13T18:10:00+01:00","rows":[{"published_at":"2026-11-09T05:02:21+01:00","url":"https://www.tiktok.com/...","duration":6,"views":72,"likes":0,"comments":0,"shares":0,"reach":null,"completion_rate":null,"average_watch_seconds":null}],"state_path":"state/tiktok_24h.json"}
A snapshot is a first observation AFTER 24h, not a historical reconstruction of exact 24h metrics.
"""
import argparse
import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

def evaluate(payload):
    now = dt.datetime.fromisoformat(payload["now"])
    if now.tzinfo is None: raise ValueError("now must include timezone")
    state_path = Path(payload.get("state_path", "state/tiktok_24h.json"))
    state = json.loads(state_path.read_text()) if state_path.exists() else {"completed": {}}
    completed = state.setdefault("completed", {})
    results = []
    for row in payload.get("rows", []):
        url = row.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ("www.tiktok.com", "tiktok.com") or "/video/" not in parsed.path: continue
        published = dt.datetime.fromisoformat(row["published_at"])
        if published.tzinfo is None or now - published < dt.timedelta(hours=24): continue
        video_id = parsed.path.rstrip("/").split("/")[-1]
        if not video_id.isdigit() or video_id in completed: continue
        result = {"video_id":video_id,"url":url,"published_at":published.isoformat(),"observed_at":now.isoformat(),"note":"First eligible snapshot after 24h; not guaranteed exact 24h values."}
        for key in ("duration","views","likes","comments","shares","reach","completion_rate","average_watch_seconds"):
            result[key] = row.get(key)
        # Do not permanently consume the once-only checkpoint when the API
        # returned no performance observations at all. Retry on a later run.
        if all(result[k] is None for k in ("views", "likes", "comments", "shares", "reach", "completion_rate", "average_watch_seconds")):
            continue
        result["decision"] = "DATEN UNZUREICHEND" if result["completion_rate"] is None or result["average_watch_seconds"] is None else "WEITERENTWICKELN ODER VERBESSERN: compare to length-matched channel median"
        completed[video_id] = result
        results.append(result)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(state_path.parent), prefix=".snapshot-")
    try:
        with os.fdopen(fd,"w") as f:
            json.dump(state,f,indent=2,ensure_ascii=False)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp,state_path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return results

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("input_json"); args=p.parse_args()
    print(json.dumps(evaluate(json.loads(Path(args.input_json).read_text())),ensure_ascii=False,indent=2))
