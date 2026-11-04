"""DealRadar data quality and monetary reporting primitives.

No merchant data or confirmed earnings are invented. All amounts retain their
original currency; pending and reversed commissions are never counted as paid.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from urllib.parse import urlparse

def money(value):
    if isinstance(value, bool):
        raise ValueError("Invalid monetary amount")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid monetary amount")
    if not number.is_finite():
        raise ValueError("Non-finite monetary amount")
    return number

def verified_offer(offer, now=None):
    now = now or datetime.now(timezone.utc)
    required = ("id", "title", "merchant", "url", "price_chf",
                "reference_price_chf", "verified_at", "reference_source",
                "reference_checked", "stock_confirmed")
    if not isinstance(offer, dict) or any(not offer.get(k) for k in required):
        return False, "missing_required_field"
    url = urlparse(str(offer["url"]))
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        return False, "invalid_https_url"
    try:
        price = money(offer["price_chf"])
        reference = money(offer["reference_price_chf"])
        checked = datetime.fromisoformat(str(offer["verified_at"]).replace("Z", "+00:00"))
        if checked.tzinfo is None or not (0 <= (now - checked).total_seconds() <= 21600):
            return False, "stale_or_future_observation"
        if price <= 0 or reference <= 0 or price >= reference:
            return False, "invalid_price_comparison"
        if (reference-price)/reference < Decimal("0.20"):
            return False, "discount_below_threshold"
    except (ValueError, TypeError, ArithmeticError):
        return False, "invalid_price_or_timestamp"
    if offer["reference_checked"] is not True or offer["stock_confirmed"] is not True:
        return False, "unverified_reference_or_stock"
    return True, "eligible_for_editorial_review"

def commission_summary(records):
    """Sum only confirmed/approved commission rows, grouped by currency."""
    totals = {}
    for row in records:
        if row.get("status") not in ("confirmed", "approved", "paid"):
            continue
        currency = row.get("currency")
        if currency not in ("CHF", "EUR"):
            continue
        amount = money(row.get("commission"))
        totals[currency] = totals.get(currency, Decimal("0")) + amount
    return {key: str(value) for key, value in sorted(totals.items())}
