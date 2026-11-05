"""Fail-closed, inspectable readiness report for dual-channel publishing."""
from __future__ import annotations
import json, os
from pathlib import Path
from zoneinfo import ZoneInfo

CONFIG = Path("config/tiktok_channels.json")

def check(config_path: Path = CONFIG) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    slots = cfg["schedule"]["channels"]
    handles = {row["handle"] for row in cfg["channels"]}
    schedule_ok = (cfg["schedule"]["timezone"] == "Europe/Zurich"
                   and len(slots) == 2
                   and all(len(s["local_times"]) == 3 and s["handle"] in handles for s in slots))
    ZoneInfo(cfg["schedule"]["timezone"])
    channels = {}
    for row in cfg["channels"]:
        handle = row["handle"]
        channels[handle] = {
            "configured": True,
            "provider": "metricool" if row.get("connected_via_metricool") else "pending",
            "provider_authorized": bool(row.get("connected_via_metricool") or row.get("api_authorized")),
            "upload_end_to_end_tested": False,
        }
    # A connection record alone never establishes upload capability.
    blockers = []
    if not schedule_ok: blockers.append("INVALID_SCHEDULE")
    if not cfg["publication"].get("enabled"): blockers.append("PUBLICATION_DISABLED")
    for handle, state in channels.items():
        if not state["provider_authorized"]: blockers.append(f"NOT_AUTHORIZED:{handle}")
        if not state["upload_end_to_end_tested"]: blockers.append(f"UPLOAD_NOT_TESTED:{handle}")
    return {"ready": not blockers, "schedule_valid": schedule_ok,
            "timezone": cfg["schedule"]["timezone"], "channels": channels,
            "blockers": blockers, "publication_attempted": False}

if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
