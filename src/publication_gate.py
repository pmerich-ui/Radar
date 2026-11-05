"""DealRadar publication safety gate: defaults to dry-run GROWTH."""
import os

def publication_decision(*, qa_passed=False, rights_verified=False, factual_claims_verified=False,
                         platform_tested=False, explicit_approval=False,
                         merchant_approved=False, tracking_tested=False,
                         swiss_delivery_verified=False, price_verified=False,
                         advertising_disclosure=False):
    mode = os.environ.get("MODE", "GROWTH").upper()
    if mode not in ("GROWTH", "MONETIZED"):
        return {"allowed": False, "reason": "INVALID_MODE"}
    if os.environ.get("DRY_RUN", "true").lower() != "false":
        return {"allowed": False, "reason": "DRY_RUN"}
    if os.environ.get("PUBLISHING_ENABLED", "false").lower() != "true":
        return {"allowed": False, "reason": "PUBLISHING_DISABLED"}
    requirements = {
        "QA": qa_passed, "RIGHTS": rights_verified,
        "FACTS": factual_claims_verified, "PLATFORM": platform_tested,
        "APPROVAL": explicit_approval,
    }
    if mode == "MONETIZED":
        requirements.update({
            "MERCHANT": merchant_approved, "TRACKING": tracking_tested,
            "SWISS_DELIVERY": swiss_delivery_verified, "PRICE": price_verified,
            "AD_DISCLOSURE": advertising_disclosure,
        })
    missing = [key for key, value in requirements.items() if value is not True]
    return {"allowed": not missing, "reason": "READY" if not missing else "MISSING_" + "_".join(missing), "mode": mode}
