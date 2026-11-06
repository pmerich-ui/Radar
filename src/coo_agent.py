"""COO operating dashboard: fail-closed targets, blockers and next actions.

Target is aspirational; no revenue is inferred from missing accounting data.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

TARGET_NET_CHF = 10000

def build(root):
    root = Path(root)
    registry = json.loads((root / "agents/registry.json").read_text(encoding="utf-8"))
    roles = registry["roles"]
    pending = sorted(p.stem for p in (root / "queue/pending").glob("*.json"))
    receipts = []
    for path in sorted((root / "queue/results").glob("*.json")):
        try:
            receipts.append(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            receipts.append({"task_id": path.stem, "status": "MALFORMED"})
    blocked = [r for r in receipts if r.get("status") in ("BLOCKED", "NEEDS_REVIEW", "MALFORMED")]
    ready = [r["id"] for r in roles if r.get("executor")]
    actions = []
    if not (root / "reports/awin_feed_status.json").is_file():
        actions.append({"priority": "P0", "owner": "05", "action": "Verify configured Awin feed and successful read-only audit", "state": "UNVERIFIED"})
    if not (root / "reports/confirmed_commissions.json").is_file():
        actions.append({"priority": "P0", "owner": "32", "action": "Connect approved commission export and reconcile confirmed net CHF", "state": "DATA_UNAVAILABLE"})
    if not (root / "reports/video_pipeline_e2e.json").is_file():
        actions.append({"priority": "P1", "owner": "18", "action": "Prove advertising brief -> render -> independent video QA", "state": "UNVERIFIED"})
    if not (root / "reports/tiktok_publication_e2e.json").is_file():
        actions.append({"priority": "P1", "owner": "24", "action": "Test platform integration without publishing until owner approval", "state": "UNVERIFIED"})
    return {"status": "OPERATING_REVIEW", "target_monthly_net_chf": TARGET_NET_CHF,
            "actual_monthly_net_chf": None, "actual_status": "DATA_UNAVAILABLE",
            "gap_to_target_chf": None, "target_is_guarantee": False,
            "role_contracts": len(roles), "registered_executors": len(ready),
            "pending_tasks": len(pending), "pending_ids": pending[:30],
            "blocked_or_review_receipts": len(blocked),
            "blocker_examples": [{"task_id": r.get("task_id"), "reason": r.get("reason", "UNKNOWN")} for r in blocked[:15]],
            "priorities": actions, "publishing_enabled": False, "new_spend_authorized": False}

def main():
    root = Path(__file__).resolve().parents[1]
    result = build(root)
    dest = root / "reports/coo_status.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "priorities": len(result["priorities"]),
                      "actual_status": result["actual_status"], "publishing_enabled": False}))

if __name__ == "__main__":
    main()
