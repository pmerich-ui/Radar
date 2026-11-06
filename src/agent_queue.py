"""DealRadar task queue: deterministic, fail-closed GitHub Actions worker.

Tasks are JSON files in queue/pending; processing writes immutable JSON receipts
in queue/results. No LLM is invoked and no external publication occurs.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue"
ALLOWED = {str(i).zfill(2) for i in range(1, 39)}
TASK_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def safe_json_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def enqueue(agent, task_id, prompt):
    if agent not in ALLOWED or not TASK_ID.fullmatch(task_id):
        raise ValueError("Invalid agent or task ID")
    if not prompt.strip() or len(prompt) > 2000:
        raise ValueError("Task description must be 1-2000 characters")
    path = QUEUE / "pending" / (task_id + ".json")
    receipt = QUEUE / "results" / (task_id + ".json")
    if path.exists() or receipt.exists():
        raise ValueError("Duplicate task ID")
    item = {"task_id":task_id,"agent_id":agent,"description":prompt,"created_at":utc_now(),"state":"PENDING"}
    safe_json_write(path,item)
    return item

def execute(item):
    agent = item["agent_id"]
    # Deterministic local agent: never pretend a prompt was processed by an LLM.
    if agent not in ALLOWED:
        return "BLOCKED", "UNKNOWN_AGENT"
    if agent in {"21","22","23"}:
        return "BLOCKED", "REQUIRES_INPUT_EVIDENCE_AND_INDEPENDENT_QA"
    if agent in {"24","25","26","27","32","33","35","36"}:
        return "BLOCKED", "EXTERNAL_AUTHORIZATION_OR_VERIFIED_DATA_REQUIRED"
    return "NEEDS_REVIEW", "ROLE_DEFINED_BUT_NO_AUTHORIZED_EXECUTOR"

def process(limit=20):
    if limit < 1 or limit > 100:
        raise ValueError("Limit out of range")
    pending = sorted((QUEUE / "pending").glob("*.json")) if (QUEUE / "pending").exists() else []
    processed=[]
    for path in pending[:limit]:
        item=json.loads(path.read_text(encoding="utf-8"))
        if item.get("task_id") != path.stem or item.get("agent_id") not in ALLOWED:
            raise ValueError("Invalid queue item: " + path.name)
        receipt=QUEUE / "results" / path.name
        if receipt.exists():
            path.unlink()  # Already processed, never execute twice
            continue
        status,reason=execute(item)
        output={"task_id":item["task_id"],"agent_id":item["agent_id"],
                "timestamp_utc":utc_now(),"status":status,"reason":reason,
                "evidence_level":"E0","source":"local deterministic queue worker",
                "published":False,"external_mutation":False}
        safe_json_write(receipt,output)
        path.unlink()
        processed.append(output)
    return processed

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="command",required=True)
    en=sub.add_parser("enqueue");en.add_argument("--agent",required=True);en.add_argument("--task-id",required=True);en.add_argument("--description",required=True)
    worker=sub.add_parser("work");worker.add_argument("--limit",type=int,default=20)
    args=parser.parse_args()
    result=enqueue(args.agent,args.task_id,args.description) if args.command=="enqueue" else process(args.limit)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
