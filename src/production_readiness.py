"""Fail-closed publishing readiness checks for DealRadar.

This module is deliberately side-effect free: it never uploads or publishes.
"""
from __future__ import annotations
import os

REQUIRED = (
    "LEDGER_URL",
    "METRICOOL_BRAND_ID",
    "AWIN_PUBLISHER_ID",
)

def readiness(environ=None):
    env = os.environ if environ is None else environ
    problems = []
    for name in REQUIRED:
        if not env.get(name, "").strip():
            problems.append(f"Missing {name}")
    db = env.get("LEDGER_URL", "")
    if db and not (db.startswith("postgresql://") or db.startswith("postgres://")):
        problems.append("Production LEDGER_URL must use PostgreSQL")
    if env.get("AWIN_PUBLISHER_ID") and env["AWIN_PUBLISHER_ID"] != "3142204":
        problems.append("Unexpected Awin publisher ID")
    if env.get("METRICOOL_BRAND_ID") and env["METRICOOL_BRAND_ID"] != "7820933":
        problems.append("Unexpected Metricool brand ID")
    if env.get("PUBLISHING_ENABLED", "").lower() != "true":
        problems.append("Publishing is disabled")
    return problems

def require_readiness(environ=None):
    problems = readiness(environ)
    if problems:
        raise RuntimeError("Fail-closed: " + "; ".join(problems))
