"""Static provider evidence, strict fail-closed runtime eligibility."""
from __future__ import annotations
import json
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("providers.json")

def load_catalog(path: Path = CATALOG_PATH) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))["providers"]
    if len({row["name"] for row in rows}) != len(rows):
        raise ValueError("duplicate provider names")
    return rows

def provider_reasons(row: dict, live: dict | None = None) -> list[str]:
    """A static catalogue listing can NEVER authorize a generation."""
    live = live or {}
    reasons = []
    if row["kind"] not in ("generator", "opensource"):
        reasons.append("not a direct video generation provider")
    if row["commercial"] != "yes":
        reasons.append("commercial rights unverified or prohibited")
    if row["free_tier"] not in ("yes", "local"):
        reasons.append("free availability not verified")
    if not live.get("authenticated_api"):
        reasons.append("no authorized automated generation adapter")
    if live.get("free_cost_chf") != 0:
        reasons.append("0 CHF cost not verified")
    free_credits = live.get("free_credits_remaining")
    required = live.get("required_free_credits")
    if not isinstance(free_credits, (int, float)) or not isinstance(required, (int, float)):
        reasons.append("live credit balance and model quote missing")
    elif free_credits < required or required < 0:
        reasons.append("insufficient free credits")
    if not live.get("license_checked_for_model"):
        reasons.append("model-specific commercial license not verified")
    if not live.get("aspect_ratio_9_16"):
        reasons.append("9:16 support not verified")
    if not live.get("min_resolution_480p"):
        reasons.append("480p output not verified")
    if not live.get("free_account_allowed"):
        reasons.append("free-tier account access not verified")
    if row["kind"] == "opensource" and not live.get("gpu_cost_zero_verified"):
        reasons.append("0 CHF GPU compute not verified")
    return reasons

def audit(rows: list[dict], live_snapshots: dict | None = None) -> list[dict]:
    live_snapshots = live_snapshots or {}
    output = []
    for row in rows:
        blockers = provider_reasons(row, live_snapshots.get(row["name"]))
        output.append({
            "name": row["name"], "site": row["url"], "category": row["kind"],
            "free": row["free_tier"], "commercial": row["commercial"],
            "evidence": row["evidence_level"], "source": row.get("source"),
            "state": "BLOCKED" if blockers else "READY",
            "reasons": blockers,
        })
    return output
