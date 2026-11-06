"""COO daily dispatch into the existing immutable agent queue.

Dispatch is idempotent per UTC date, creates internal work orders only.
Never publishes, spends money, or asserts that a video was produced.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
from . import agent_queue

def dispatch(root=None, day=None):
    root = Path(root or agent_queue.ROOT)
    day = day or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    if not (len(day) == 8 and day.isascii() and day.isdigit()):
        raise ValueError("Invalid day")
    orders = (
        ("18", "produce", "Prepare one new vertical advertising video draft with verified source material. No publication."),
        ("21", "qa", "Independently review today's video draft, technical parameters and rights evidence. Do not approve without evidence."),
        ("24", "publish", "Check whether an approved video can be published today. If not, report blocker. Never publish without explicit owner approval and gate."),
    )
    created, existing = [], []
    for agent, label, description in orders:
        task_id = f"coo-{day}-{label}"
        pending = root / "queue/pending" / (task_id + ".json")
        receipt = root / "queue/results" / (task_id + ".json")
        if pending.exists() or receipt.exists():
            existing.append(task_id)
            continue
        # agent_queue uses a module-level root; supply no arbitrary remote paths.
        item = {"task_id": task_id, "agent_id": agent,
                "description": description, "depends_on": [],
                "created_at": agent_queue.utc_now(), "state": "PENDING",
                "origin": "COO_DAILY_DISPATCH"}
        agent_queue.safe_json_write(pending, item)
        created.append(task_id)
    return {"day_utc": day, "created": created, "existing": existing,
            "publication_authorized": False, "external_actions": False}

def main():
    root = agent_queue.ROOT
    result = dispatch(root)
    path = root / "reports/coo_dispatch.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
