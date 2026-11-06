"""Read-only Awin feed executor. Uses only a local, pre-approved .csv.gz file.

No downloads, API credentials, affiliate links, network calls, or publication.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .awin_feed_audit import audit

def run(feed_path, *, root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    allowed = (root / "data" / "awin" / "incoming").resolve()
    feed = Path(feed_path)
    if feed.is_absolute():
        raise ValueError("Absolute feed paths are forbidden")
    candidate = (root / feed).resolve()
    if not candidate.is_relative_to(allowed) or candidate.suffixes[-2:] != [".csv", ".gz"]:
        raise ValueError("Only local data/awin/incoming/*.csv.gz feeds allowed")
    if not candidate.is_file():
        return {"status": "BLOCKED", "reason": "AWIN_FEED_UNAVAILABLE",
                "evidence_level": "E0", "publishable_deals": 0}
    if candidate.stat().st_size > 100 * 1024 * 1024:
        return {"status": "BLOCKED", "reason": "AWIN_FEED_TOO_LARGE",
                "evidence_level": "E0", "publishable_deals": 0}
    digest = hashlib.sha256()
    with candidate.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    try:
        details = audit(candidate)
    except (OSError, ValueError, UnicodeError, KeyError, EOFError) as exc:
        return {"status": "BLOCKED", "reason": "AWIN_FEED_INVALID",
                "evidence_level": "E0", "publishable_deals": 0,
                "error_type": type(exc).__name__}
    return {"status": "COMPLETED", "reason": "AWIN_READ_ONLY_AUDIT",
            "evidence_level": "E2", "source_sha256": digest.hexdigest(),
            "source": str(candidate.relative_to(root)),
            "publishable_deals": 0, "audit": details}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.feed), ensure_ascii=False, indent=2))
