"""Daily offline video draft pipeline: Agent 18 render, Agent 21 independent QA.

Generic original illustrations only; not verified product advertising.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from .producer import produce
from .video_qa_agent import inspect

def run(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).isoformat()
    result = produce(root / "media")
    video = result.get("file")
    qa = inspect(video) if video else {"status": "BLOCKED", "reason": result.get("status", "NO_VIDEO")}
    passed = qa.get("status") == "TECHNICAL_PASS"
    entry = {
        "created_at_utc": today, "agent_18": result.get("status"),
        "agent_21": qa, "video_file": Path(video).name if video else None,
        "sha256": hashlib.sha256(Path(video).read_bytes()).hexdigest() if video and passed else None,
        "status": "QA_PASSED" if passed else "BLOCKED",
        "creative_review": "REQUIRED", "rights_review": "REQUIRED",
        "merchant_approval": "NOT_VERIFIED", "owner_approval": False,
        "publication": "NOT_AUTHORIZED", "platform_post_id": None,
        "publishable": False,
        "note": "Generic illustrated shopping content, not a verified affiliate product ad."
    }
    out = root / "daily_video_report.json"
    out.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": entry["status"], "video_file": entry["video_file"],
                      "publishable": False, "report": str(out)}))
    return entry

if __name__ == "__main__":
    run(Path(os.environ.get("VIDEO_OUTPUT_DIR", "output/daily")))
