"""DealRadar zero-CHF video provider router. No publishing or paid calls.

Providers must be independently connected and have verified commercial rights.
A failed provider never triggers an unapproved charge or a second paid attempt.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
import os

class Status(str, Enum):
    READY = "READY"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    GENERATED = "GENERATED"
    HOLD = "HOLD"

@dataclass(frozen=True)
class Provider:
    name: str
    free_credits: Optional[int]
    estimated_credits: Optional[int]
    commercial_rights_verified: bool
    connected: bool
    watermark_allowed: bool = True

@dataclass(frozen=True)
class Attempt:
    provider: str
    status: Status
    reason: str
    video_url: Optional[str] = None

def eligible(p: Provider) -> tuple[bool, str]:
    if not p.connected:
        return False, "not connected"
    if not p.commercial_rights_verified:
        return False, "commercial license unverified"
    if p.free_credits is None or p.estimated_credits is None:
        return False, "free quota or generation cost unverified"
    if p.estimated_credits > p.free_credits:
        return False, "insufficient free credits"
    return True, "eligible"

def route(providers: list[Provider], generate: Callable[[Provider], str],
          verify: Callable[[str], bool], *, max_attempts: int = 8) -> list[Attempt]:
    """Calls only eligible providers. verify must inspect a real generated file."""
    history: list[Attempt] = []
    if os.getenv("DEALRADAR_ALLOW_FREE_GENERATION") != "1":
        return [Attempt("router", Status.HOLD, "generation disabled; set explicit opt-in")]
    for p in providers[:max_attempts]:
        ok, reason = eligible(p)
        if not ok:
            history.append(Attempt(p.name, Status.SKIPPED, reason))
            continue
        try:
            url = generate(p)
            if not url or not url.startswith(("https://", "http://")):
                raise ValueError("no real output URL")
            if not verify(url):
                history.append(Attempt(p.name, Status.HOLD, "output verification failed"))
                continue
            history.append(Attempt(p.name, Status.GENERATED, "verified", url))
            return history
        except Exception as exc:
            history.append(Attempt(p.name, Status.FAILED, type(exc).__name__))
    return history

# No provider is enabled by default: verified licenses and credit quotes
# must be supplied from authenticated provider APIs before enabling one.
DEFAULT_PROVIDERS = [
    Provider(name, None, None, False, False)
    for name in ("Leonardo", "Google Flow", "Dreamina", "PixVerse",
                 "Kling", "Bing Video Creator", "Krea", "Runway",
                 "Adobe Firefly", "Hugging Face Wan")
]
