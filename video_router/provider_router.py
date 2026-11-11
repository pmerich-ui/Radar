"""Safe provider routing. Only official authenticated adapters can be supplied.

Website scraping, login bypasses, payments, and publishing are intentionally absent.
"""
from __future__ import annotations
from typing import Callable
from .catalog import audit, load_catalog

def route_catalog(live_snapshots: dict[str, dict],
                  adapters: dict[str, Callable[[dict], str]],
                  verify_output: Callable[[str], bool],
                  *, approved_free_generation: bool = False,
                  max_real_attempts: int = 6) -> dict:
    records = audit(load_catalog(), live_snapshots)
    if not approved_free_generation:
        return {"status": "HOLD", "reason": "free-generation opt-in not enabled",
                "attempts": [], "catalogue": records}
    attempts = []
    real_attempts = 0
    for entry in records:
        if entry["state"] != "READY":
            continue
        name = entry["name"]
        if name not in adapters:
            attempts.append({"name": name, "status": "SKIPPED",
                             "reason": "no authenticated integration installed"})
            continue
        if real_attempts >= max_real_attempts:
            break
        real_attempts += 1
        try:
            # Integrations must implement their own idempotency keys and wait for a
            # confirmed completion; never resubmit an ambiguous in-flight job.
            url = adapters[name](live_snapshots[name])
            if not isinstance(url, str) or not url.startswith("https://"):
                raise ValueError("no confirmed HTTPS output URL")
            if not verify_output(url):
                attempts.append({"name": name, "status": "REVIEW_REQUIRED",
                                 "reason": "real media verification failed"})
                continue
            attempts.append({"name": name, "status": "GENERATED",
                             "video_url": url})
            return {"status": "GENERATED_UNPUBLISHED", "attempts": attempts,
                    "catalogue": records}
        except Exception as err:
            # Do not leak prompt text or credentials into the audit trail.
            attempts.append({"name": name, "status": "FAILED",
                             "error_type": type(err).__name__})
    return {"status": "NO_VERIFIED_VIDEO", "attempts": attempts, "catalogue": records}
