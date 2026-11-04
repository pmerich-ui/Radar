"""Strict, auditable DealRadar content lifecycle. No automatic publishing."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from urllib.parse import urlparse
import statistics

class Status(str, Enum):
    DISCOVERED = "DISCOVERED"
    VERIFIED = "VERIFIED"
    RENDERED = "RENDERED"
    QA_PASSED = "QA_PASSED"
    DRAFT_REQUESTED = "DRAFT_REQUESTED"
    DRAFT_CONFIRMED = "DRAFT_CONFIRMED"
    PUBLISHED_CONFIRMED = "PUBLISHED_CONFIRMED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"

NEXT = {
    Status.DISCOVERED: {Status.VERIFIED, Status.REJECTED},
    Status.VERIFIED: {Status.RENDERED, Status.EXPIRED, Status.REJECTED},
    Status.RENDERED: {Status.QA_PASSED, Status.REJECTED},
    Status.QA_PASSED: {Status.DRAFT_REQUESTED, Status.REJECTED},
    Status.DRAFT_REQUESTED: {Status.DRAFT_CONFIRMED, Status.REJECTED},
    Status.DRAFT_CONFIRMED: {Status.PUBLISHED_CONFIRMED, Status.REJECTED},
    Status.PUBLISHED_CONFIRMED: {Status.EXPIRED},
    Status.EXPIRED: set(),
    Status.REJECTED: set(),
}

def transition(current: str, target: str, evidence: str | None = None) -> str:
    src, dst = Status(current), Status(target)
    if dst not in NEXT[src]:
        raise ValueError(f"Forbidden transition: {src.value} -> {dst.value}")
    if dst in (Status.VERIFIED, Status.QA_PASSED, Status.DRAFT_CONFIRMED, Status.PUBLISHED_CONFIRMED) and not evidence:
        raise ValueError(f"{dst.value} requires independent evidence")
    return dst.value

def verified_deal(offer: dict, now: datetime | None = None) -> bool:
    """Fail closed: no unsupported discount or price-history claims."""
    now = now or datetime.now(timezone.utc)
    if offer.get("status") != "verified" or not offer.get("evidence_url"):
        return False
    for key in ("url", "evidence_url"):
        u = urlparse(str(offer.get(key, "")))
        if u.scheme != "https" or not u.hostname:
            return False
    price = offer.get("price_chf")
    if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
        return False
    try:
        verified = datetime.fromisoformat(offer["verified_at"].replace("Z", "+00:00"))
        if verified.tzinfo is None or verified > now or (now-verified).total_seconds() > 86400:
            return False
        if offer.get("valid_until"):
            until = datetime.fromisoformat(offer["valid_until"].replace("Z", "+00:00"))
            if until.tzinfo is None or until <= now:
                return False
    except (ValueError, TypeError, KeyError, AttributeError):
        return False
    return True

def ninety_day_median(history: list[dict], now: datetime | None = None) -> float | None:
    """Compute median from actual dated observations; no fabricated reference prices."""
    now = now or datetime.now(timezone.utc)
    prices = []
    for observation in history:
        try:
            timestamp = datetime.fromisoformat(observation["at"].replace("Z", "+00:00"))
            price = observation["price_chf"]
            if timestamp.tzinfo is None or not 0 <= (now-timestamp).total_seconds() <= 90*86400:
                continue
            if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
                continue
            prices.append(float(price))
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
    # A single price point is not a credible historical baseline.
    return round(statistics.median(prices), 2) if len(prices) >= 10 else None
