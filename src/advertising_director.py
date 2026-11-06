"""Agent 14: evidence-first advertising brief for Swiss consumer offers.

Produces a review-only creative brief. No unverified discount or conversion claims.
"""
import json
from pathlib import Path

def build_brief(offer):
    required = ("product_name", "merchant_name", "price_chf", "product_url")
    missing = [key for key in required if not offer.get(key)]
    if missing:
        return {"status": "BLOCKED", "reason": "MISSING_" + "_".join(missing),
                "publishable": False}
    price = offer["price_chf"]
    if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
        return {"status": "BLOCKED", "reason": "INVALID_PRICE", "publishable": False}
    name = str(offer["product_name"]).strip()
    merchant = str(offer["merchant_name"]).strip()
    if not name or not merchant or len(name) > 160 or len(merchant) > 100:
        return {"status": "BLOCKED", "reason": "INVALID_PRODUCT", "publishable": False}
    price_text = f"CHF {price:.2f}"
    return {
        "status": "DRAFT_REVIEW", "publishable": False,
        "agent": "14", "format": "vertical_9_16", "duration_target_seconds": 18,
        "audience": "Schweizer Konsumentinnen und Konsumenten",
        "creative": {
            "hook": f"{name}: Lohnt sich das Angebot?",
            "sequence": [
                {"seconds": "0-3", "message": f"{name}: Preischeck"},
                {"seconds": "3-9", "message": "Produkt und konkrete Eigenschaften nur mit belegtem Bildmaterial zeigen"},
                {"seconds": "9-14", "message": f"Angebotspreis {price_text} bei {merchant} (Stand prüfen)"},
                {"seconds": "14-18", "message": "Aktuellen Endpreis und Lieferbedingungen prüfen"}
            ],
            "disclosure": "Werbung | Affiliate-Link",
            "cta": "Angebot und Versandbedingungen prüfen"
        },
        "blocked_until_verified": [
            "merchant_approval", "swiss_delivery", "current_price",
            "rights", "independent_fact_check", "video_qa", "owner_approval"
        ],
        "no_unverified_claims": True
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--offer", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.offer).read_text(encoding="utf-8"))
    result = build_brief(data)
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "publishable": False}))

if __name__ == "__main__":
    main()
