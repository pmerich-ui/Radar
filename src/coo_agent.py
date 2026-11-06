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
    # A published video requires an independently recorded platform ID and timestamp.
    # Drafts, uploads, schedules and generated files do not count as live.
    today = datetime.now(timezone.utc).date().isoformat()
    ledger = root / "reports/video_publications.json"
    records = []
    if ledger.is_file():
        try:
            payload = json.loads(ledger.read_text(encoding="utf-8"))
            records = payload if isinstance(payload, list) else payload.get("publications", [])
            if not isinstance(records, list):
                records = []
        except (OSError, ValueError, AttributeError):
            records = []
    live = [r for r in records if isinstance(r, dict)
            and r.get("status") == "PUBLISHED_CONFIRMED"
            and r.get("platform_post_id") and r.get("published_at_utc", "").startswith(today)]
    produced = [r for r in records if isinstance(r, dict)
                and r.get("status") in ("RENDERED", "QA_PASSED", "PUBLISHED_CONFIRMED")
                and r.get("created_at_utc", "").startswith(today)]
    if not produced:
        actions.insert(0, {"priority": "P0", "owner": "18",
                           "action": "Produce and technically QA a new video today; diagnose render or source blockers",
                           "state": "DAILY_PRODUCTION_NOT_VERIFIED"})
    if not live:
        actions.insert(0, {"priority": "P0", "owner": "24",
                           "action": "Check approval, rights, QA and publishing connection; prepare approved video for publishing; escalate if blocked",
                           "state": "DAILY_PUBLICATION_NOT_VERIFIED"})
    return {"status": "OPERATING_REVIEW", "daily_target_produced": 1,
            "daily_target_published": 1, "utc_day": today,
            "produced_today_verified": len(produced),
            "published_today_verified": len(live),
            "publication_evidence": "platform_post_id plus published_at_utc; never count upload as publication",
            "remediation_triggered": not produced or not live,
            "remediation_mode": "ESCALATE_AND_PREPARE_ONLY; NO_UNAPPROVED_PUBLISHING", "target_monthly_net_chf": TARGET_NET_CHF,
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
