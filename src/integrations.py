"""DealRadar integration registry: fail-closed capability checks.

ChatGPT app connections are not automatically runtime API credentials.
Enable a provider only after its server-side credentials and a real health check exist.
"""
from __future__ import annotations
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Provider:
    name: str
    purpose: str
    required_env: tuple[str, ...]
    mode: str = "read_only"
    production_allowed: bool = False

PROVIDERS = (
    Provider("awin", "approved CHF affiliate feeds and confirmed commissions", ("AWIN_API_TOKEN", "AWIN_PUBLISHER_ID")),
    Provider("channel3", "product discovery; requires independent CHF and merchant verification", ("CHANNEL3_API_KEY",)),
    Provider("posthog", "landing-page events and click-funnel analytics", ("POSTHOG_PROJECT_KEY", "POSTHOG_HOST"), "analytics"),
    Provider("veed", "optional AI video production with credit budget", ("VEED_API_KEY",), "render_only"),
    Provider("visla", "optional licensed video production", ("VISLA_API_KEY",), "render_only"),
    Provider("composio", "optional cross-app orchestration", ("COMPOSIO_API_KEY",), "orchestration"),
    Provider("metricool", "social analytics and approved draft scheduling", ("METRICOOL_API_TOKEN",), "analytics"),
)

def status(environ=None):
    env = os.environ if environ is None else environ
    return [{
        "provider": p.name,
        "purpose": p.purpose,
        "mode": p.mode,
        "configured": all(bool(env.get(k)) for k in p.required_env),
        "production_allowed": p.production_allowed,
        "verified": False,  # never infer live access from environment variables
    } for p in PROVIDERS]

def can_publish(*, verified_deal: bool, qa_passed: bool, platform_approved: bool, draft_confirmed: bool) -> bool:
    return all((verified_deal, qa_passed, platform_approved, draft_confirmed))

def revenue_state(*, awin_connected: bool, transactions_checked: bool, confirmed_chf=None):
    if not awin_connected or not transactions_checked or confirmed_chf is None:
        return {"status": "unmeasurable", "confirmed_chf": None}
    if isinstance(confirmed_chf, bool) or not isinstance(confirmed_chf, (int, float)) or confirmed_chf < 0:
        raise ValueError("Invalid confirmed commission")
    return {"status": "measured", "confirmed_chf": round(float(confirmed_chf), 2)}
