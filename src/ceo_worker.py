"""24/7 DealRadar CEO heartbeat worker. No publishing, paid API or fake agent execution."""
import datetime as dt
import json
import os
import pathlib
import signal
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
INTERVAL = max(30, min(3600, int(os.getenv("HEARTBEAT_SECONDS", "60"))))
running = True

def stop(*_):
    global running
    running = False

def tick():
    registry = json.loads((ROOT / "agents" / "registry.json").read_text(encoding="utf-8"))
    roles = registry.get("roles", [])
    ids = [r.get("id") for r in roles]
    if ids != [f"{i:02d}" for i in range(1, 39)]:
        raise RuntimeError("INVALID_AGENT_REGISTRY")
    contracts = sum((ROOT / "agents" / f"{r['id']}-{r['slug']}.md").is_file() for r in roles)
    if contracts != 38:
        raise RuntimeError(f"INCOMPLETE_CONTRACTS_{contracts}")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    print(json.dumps({
        "timestamp_utc": now, "service": "dealradar-ceo-v3",
        "status": "HEALTHY", "registered_agent_contracts": 38,
        "verified_live_executors": 0,
        "publishing_enabled": False, "external_paid_actions_enabled": False,
        "mode": "SAFE_MONITOR_ONLY",
        "note": "Heartbeat proves worker uptime, not 38 agents executing."
    }), flush=True)

def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while running:
        try:
            tick()
        except Exception as exc:
            print(json.dumps({"status": "ERROR", "reason": str(exc)[:160]}), flush=True)
        for _ in range(INTERVAL):
            if not running:
                break
            time.sleep(1)

if __name__ == "__main__":
    main()
