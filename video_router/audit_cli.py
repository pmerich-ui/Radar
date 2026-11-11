"""Read-only audit of provider catalogue; no provider API or credit usage."""
from __future__ import annotations
import json
try:
    from .catalog import audit, load_catalog
except ImportError:
    from catalog import audit, load_catalog

def main():
    rows = load_catalog()
    report = {
        "date": "2026-11-11",
        "scope": "Public evidence and earlier connected-account snapshots",
        "not_live_provider_account_probes": True,
        "additional_cost_chf": 0,
        "generation_attempts": 0,
        "provider_count": len(rows),
        "providers": audit(rows),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
