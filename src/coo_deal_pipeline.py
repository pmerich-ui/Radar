"""COO: scan Awin candidates and create safe Agent 14 review briefs in one run.

No URLs or product-level feed contents are exported as GitHub artifacts.
"""
import json
import os
from pathlib import Path
from .awin_feed_fetch import download_and_audit
from .coo_deal_discovery import scan
from .advertising_director import build_brief

def run(root):
    root = Path(root)
    result = {"status": "BLOCKED", "reason": "AWIN_FEED_URL_NOT_CONFIGURED",
              "candidates": 0, "briefs_created": 0, "publishable": False}
    url = os.environ.get("AWIN_FEED_URL", "")
    if not url:
        return result
    def select(feed_root):
        selection = scan(feed_root, limit=20)
        briefs = [build_brief(item) for item in selection["candidates"]]
        result.update({"status": "DRAFT_REVIEW" if briefs else "NO_CANDIDATES",
                       "reason": "MERCHANT_APPROVAL_PRICE_DELIVERY_RIGHTS_NOT_VERIFIED",
                       "candidates": len(briefs),
                       "briefs_created": sum(b["status"] == "DRAFT_REVIEW" for b in briefs),
                       "publishable": False})
        # Product-level details and affiliate links stay within ephemeral runner only.
        # Do not expose them through public logs, reports or artifacts.
    try:
        audit = download_and_audit(url, root=root, candidate_callback=select)
        audit_path = root / "reports/awin_feed_status.json"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if audit.get("status") != "COMPLETED":
            result.update(status="BLOCKED", reason="AWIN_AUDIT_FAILED")
    except Exception as exc:
        result.update(status="BLOCKED", reason="AWIN_FETCH_OR_SELECTION_FAILED",
                      error_type=type(exc).__name__)
    return result

def main():
    root = Path(__file__).resolve().parents[1]
    result = run(root)
    output = root / "reports/coo_deal_pipeline.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    # A blocked import must fail the GitHub Actions step; an exit code of zero
    # would otherwise make a broken Awin pipeline appear healthy.
    return 2 if result["status"] == "BLOCKED" else 0

if __name__ == "__main__":
    raise SystemExit(main())
