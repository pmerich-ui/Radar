"""DealRadar task queue: deterministic, fail-closed GitHub Actions worker.

Tasks are JSON files in queue/pending; processing writes immutable JSON receipts
in queue/results. No LLM is invoked and no external publication occurs.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue"
ALLOWED = {str(i).zfill(2) for i in range(1, 39)}
TASK_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def safe_json_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError("Immutable receipt already exists: " + path.name)
    # Exclusive creation: never overwrite an existing task or evidence receipt.
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

def enqueue(agent, task_id, prompt, depends_on=None):
    if agent not in ALLOWED or not TASK_ID.fullmatch(task_id):
        raise ValueError("Invalid agent or task ID")
    if not prompt.strip() or len(prompt) > 2000:
        raise ValueError("Task description must be 1-2000 characters")
    path = QUEUE / "pending" / (task_id + ".json")
    receipt = QUEUE / "results" / (task_id + ".json")
    if path.exists() or receipt.exists():
        raise ValueError("Duplicate task ID")
    deps = depends_on or []
    if len(deps) > 20 or len(set(deps)) != len(deps) or any(not TASK_ID.fullmatch(d) or d == task_id for d in deps):
        raise ValueError("Invalid dependencies")
    item = {"task_id": task_id, "agent_id": agent, "description": prompt,
            "depends_on": deps, "created_at": utc_now(), "state": "PENDING"}
    safe_json_write(path, item)
    return item

def execute(item):
    agent = item["agent_id"]
    # Definition != executor. Never pretend this is an LLM or a publisher.
    if agent not in ALLOWED:
        return "BLOCKED", "UNKNOWN_AGENT"
    if agent == "02":
        registry = ROOT / "agents" / "registry.json"
        if not registry.exists():
            return "BLOCKED", "REGISTRY_MISSING"
        roles = json.loads(registry.read_text(encoding="utf-8")).get("roles", [])
        contracts = sum((ROOT / "agents" / (r["id"] + "-" + r["slug"] + ".md")).is_file() for r in roles)
        if len(roles) != 38 or contracts != 38:
            return "BLOCKED", f"INCOMPLETE_AGENTS_{contracts}_OF_{len(roles)}"
        return "COMPLETED", "VERIFIED_38_AGENT_CONTRACTS"
    if agent == "37":
        requirements = ["src/publication_gate.py", "src/agent_queue.py",
                        ".github/workflows/agent-task-queue.yml", "tests/test_agent_queue.py"]
        missing = [p for p in requirements if not (ROOT / p).is_file()]
        return ("BLOCKED", "MISSING_" + ",".join(missing)) if missing else ("COMPLETED", "LOCAL_WORKFLOW_FILES_VERIFIED_NO_RUNTIME_CLAIM")
    if agent in {"21", "22", "23"}:
        return "BLOCKED", "REQUIRES_INPUT_EVIDENCE_AND_INDEPENDENT_QA"
    if agent in {"24", "25", "26", "27", "32", "33", "35", "36"}:
        return "BLOCKED", "EXTERNAL_AUTHORIZATION_OR_VERIFIED_DATA_REQUIRED"
    return "NEEDS_REVIEW", "ROLE_DEFINED_BUT_NO_AUTHORIZED_EXECUTOR"

def process(limit=20):
    if limit < 1 or limit > 100:
        raise ValueError("Limit out of range")
    pending = sorted((QUEUE / "pending").glob("*.json")) if (QUEUE / "pending").exists() else []
    processed = []
    for path in pending[:limit]:
        item = json.loads(path.read_text(encoding="utf-8"))
        if item.get("task_id") != path.stem or item.get("agent_id") not in ALLOWED:
            raise ValueError("Invalid queue item: " + path.name)
        receipt = QUEUE / "results" / path.name
        if receipt.exists():
            path.unlink()  # A receipt already exists: never execute twice.
            continue
        deps = item.get("depends_on", [])
        if not isinstance(deps, list) or any(not isinstance(d, str) or not TASK_ID.fullmatch(d) or d == item["task_id"] for d in deps):
            raise ValueError("Invalid dependencies in " + path.name)
        receipts = [QUEUE / "results" / (d + ".json") for d in deps]
        if any(not p.exists() for p in receipts):
            continue  # Wait; never prematurely claim execution.
        if any(json.loads(p.read_text(encoding="utf-8")).get("status") != "COMPLETED" for p in receipts):
            status, reason = "BLOCKED", "DEPENDENCY_NOT_COMPLETED"
        else:
            status, reason = execute(item)
        output = {"task_id": item["task_id"], "agent_id": item["agent_id"],
                  "timestamp_utc": utc_now(), "status": status, "reason": reason,
                  "evidence_level": "E0", "source": "local deterministic queue worker",
                  "published": False, "external_mutation": False}
        safe_json_write(receipt, output)
        path.unlink()
        processed.append(output)
    return processed

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    en = sub.add_parser("enqueue")
    en.add_argument("--agent", required=True)
    en.add_argument("--task-id", required=True)
    en.add_argument("--description", required=True)
    en.add_argument("--depends-on", default="", help="Comma-separated prerequisite task IDs")
    worker = sub.add_parser("work")
    worker.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    result = enqueue(args.agent, args.task_id, args.description, [s.strip() for s in args.depends_on.split(",") if s.strip()]) if args.command == "enqueue" else process(args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
