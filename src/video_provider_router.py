"""Fail-closed provider selection for DealRadar video jobs.

No external requests, charges, or publishing happen in this module.
Providers are configured through VIDEO_PROVIDER_REGISTRY_JSON.
"""
import json
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Provider:
    name: str
    enabled: bool
    commercial_rights: bool
    supports_vertical: bool
    credits: int
    cost_credits: int
    priority: int

def registry(raw=None):
    raw = os.environ.get("VIDEO_PROVIDER_REGISTRY_JSON", "[]") if raw is None else raw
    entries = json.loads(raw)
    if not isinstance(entries, list):
        raise ValueError("Provider registry must be an array")
    names = set()
    result = []
    for entry in entries:
        p = Provider(
            name=str(entry["name"]),
            enabled=entry["enabled"] is True,
            commercial_rights=entry["commercial_rights"] is True,
            supports_vertical=entry["supports_vertical"] is True,
            credits=int(entry["credits"]),
            cost_credits=int(entry["cost_credits"]),
            priority=int(entry["priority"]),
        )
        if not p.name or p.name in names or p.credits < 0 or p.cost_credits < 0:
            raise ValueError("Invalid provider configuration")
        names.add(p.name)
        result.append(p)
    return sorted(result, key=lambda p: (p.priority, p.name))

def candidates(providers, max_credits=0):
    """Default zero-cost policy. Paid providers require explicit per-job budget."""
    if max_credits < 0:
        raise ValueError("Negative budget")
    return [p for p in providers if p.enabled and p.commercial_rights
            and p.supports_vertical and p.cost_credits <= p.credits
            and p.cost_credits <= max_credits]

def plan(raw=None, max_credits=0):
    selected = candidates(registry(raw), max_credits)
    return {
        "status": "READY_FOR_ADAPTER_EXECUTION" if selected else "BLOCKED_NO_ELIGIBLE_PROVIDER",
        "providers": [p.name for p in selected],
        "max_credits_per_job": max_credits,
        "execution": False,
        "publication_authorized": False,
    }

def fallback(providers, attempt, max_credits=0):
    """Caller supplies attempt(provider)->result; fail closed on every exception.
    Only retry a provider if caller can prove its attempt did not incur a charge.
    """
    outcomes = []
    for p in candidates(providers, max_credits):
        try:
            result = attempt(p)
            if result.get("status") == "SUCCEEDED" and result.get("verified_file"):
                return {"status": "RENDERED_UNREVIEWED", "provider": p.name,
                        "file": result["verified_file"], "attempts": outcomes,
                        "publication_authorized": False}
            outcomes.append({"provider": p.name, "status": result.get("status", "UNKNOWN")})
            if result.get("charged") or result.get("status") in ("UNKNOWN", "PENDING", "TIMEOUT"):
                break  # avoid duplicate charges for uncertain outcomes
        except Exception:
            outcomes.append({"provider": p.name, "status": "UNKNOWN"})
            break
    return {"status": "BLOCKED", "attempts": outcomes, "publication_authorized": False}
