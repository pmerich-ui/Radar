"""Metricool MCP hand-off with durable, idempotent release receipts.

GitHub Actions cannot invoke a ChatGPT-connected Metricool MCP account.
The authorized MCP caller invokes `dispatch(..., update_post=...)` after
technical/creative/rights review and writes the resulting receipt. This code
does NOT claim that a scheduled post is already live on TikTok.
"""
from __future__ import annotations

import copy
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from src.media_recovery_v8 import publication_ready

BRAND_ID = 7820933
TIMEZONE = "Europe/Zurich"
HOSTS = frozenset({"static.metricool.com", "videogen.vidiq.com"})
REQUIRED_STATES = frozenset({"SCHEDULED", "PUBLISHED_VERIFIED"})


class ReleaseBlocked(ValueError):
    pass


def build_update(post: dict, media_url: str, qa: dict, evidence: dict,
                 job: dict, when: datetime) -> dict:
    """Produce full Metricool update body, never mutate the original draft."""
    if not publication_ready(job, qa, evidence):
        raise ReleaseBlocked("QUALITY_RIGHTS_OR_CREATIVE_EVIDENCE_MISSING")
    if not isinstance(when, datetime) or when.tzinfo is None:
        raise ReleaseBlocked("TIMEZONE_REQUIRED")
    local = when.astimezone(ZoneInfo(TIMEZONE))
    if local <= datetime.now(ZoneInfo(TIMEZONE)):
        raise ReleaseBlocked("PUBLICATION_TIME_IN_PAST")
    uri = urlsplit(media_url)
    if (uri.scheme != "https" or uri.hostname not in HOSTS
            or uri.username or uri.password or uri.port not in (None, 443)):
        raise ReleaseBlocked("UNTRUSTED_MEDIA_URL")
    networks = [x.get("network") for x in post.get("providers", [])]
    if networks != ["tiktok"]:
        raise ReleaseBlocked("ONLY_AUTHORIZED_TIKTOK_ACCOUNT")
    if not post.get("uuid") or not post.get("id") or not post.get("text"):
        raise ReleaseBlocked("INCOMPLETE_METRICOOL_POST")

    # Only the TikTok network payload belongs to the TikTok provider.
    tiktok = copy.deepcopy(post.get("tiktokData", {}))
    tiktok.update({"privacyOption": "PUBLIC_TO_EVERYONE", "isAigc": True,
                   "commercialContentOwnBrand": True})
    result = {
        "publicationDate": {"dateTime": local.strftime("%Y-%m-%dT%H:%M:%S"),
                            "timezone": TIMEZONE},
        "text": post["text"],
        "firstCommentText": post.get("firstCommentText", ""),
        "providers": [{"network": "tiktok"}],
        "media": [media_url],
        "mediaAltText": [None],
        "saveExternalMediaFiles": True,
        "autoPublish": True,
        "draft": False,
        "shortener": post.get("shortener", False),
        "smartLinkData": post.get("smartLinkData", {"ids": []}),
        "tiktokData": tiktok,
        "hasNotReadNotes": post.get("hasNotReadNotes", False),
        "brandTags": post.get("brandTags", []),
    }
    return {"id": str(post["id"]), "uuid": str(post["uuid"]),
            "blogId": str(BRAND_ID), "info": json.dumps(result, ensure_ascii=False)}


class ReleaseLedger:
    """State transitions resist concurrent duplicate sends and uncertain results."""
    def __init__(self, dbfile: str | Path):
        self.db = sqlite3.connect(str(dbfile), timeout=30, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS metricool_release (
            uuid TEXT PRIMARY KEY, sha256 TEXT NOT NULL, status TEXT NOT NULL,
            post_id TEXT, receipt TEXT, public_url TEXT)""")

    def claim(self, uuid: str, sha256: str) -> dict:
        if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
            raise ReleaseBlocked("INVALID_MEDIA_SHA256")
        with self.db:
            cur = self.db.execute(
                "INSERT OR IGNORE INTO metricool_release(uuid,sha256,status) VALUES(?,?,'DISPATCH_STARTED')",
                (uuid, sha256))
            row = self.db.execute(
                "SELECT sha256,status,post_id,public_url FROM metricool_release WHERE uuid=?",
                (uuid,)).fetchone()
        if row[0] != sha256:
            raise ReleaseBlocked("POST_ALREADY_RESERVED_FOR_OTHER_MEDIA")
        return {"claimed": cur.rowcount == 1, "status": row[1],
                "post_id": row[2], "public_url": row[3]}

    def receipt(self, uuid: str, sha256: str, result: dict) -> dict:
        data = result.get("data", result)
        if not isinstance(data, dict) or str(data.get("uuid")) != uuid:
            raise ReleaseBlocked("METRICOOL_UUID_NOT_CONFIRMED")
        if data.get("draft") is not False or data.get("autoPublish") is not True:
            raise ReleaseBlocked("METRICOOL_STILL_DRAFT_OR_MANUAL")
        if not data.get("id") or not any(
                p.get("network") == "tiktok" for p in data.get("providers", [])):
            raise ReleaseBlocked("METRICOOL_SCHEDULE_NOT_CONFIRMED")
        with self.db:
            row = self.db.execute("SELECT sha256 FROM metricool_release WHERE uuid=?",
                                  (uuid,)).fetchone()
            if not row or row[0] != sha256:
                raise ReleaseBlocked("RELEASE_NOT_CLAIMED")
            self.db.execute(
                "UPDATE metricool_release SET status='SCHEDULED',post_id=?,receipt=? WHERE uuid=?",
                (str(data["id"]), json.dumps(data), uuid))
        return {"status": "SCHEDULED", "metricool_id": str(data["id"]),
                "uuid": uuid, "public_url": None}

    def uncertain(self, uuid: str):
        with self.db:
            self.db.execute("UPDATE metricool_release SET status='RECONCILE_REQUIRED' "
                            "WHERE uuid=? AND status='DISPATCH_STARTED'", (uuid,))

    def published(self, uuid: str, url: str):
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname not in
                {"www.tiktok.com", "tiktok.com", "vm.tiktok.com"}
                or "/video/" not in parsed.path):
            raise ReleaseBlocked("PUBLIC_TIKTOK_URL_REQUIRED")
        with self.db:
            cur = self.db.execute(
                "UPDATE metricool_release SET status='PUBLISHED_VERIFIED', public_url=? "
                "WHERE uuid=? AND status='SCHEDULED'", (url, uuid))
            if cur.rowcount != 1:
                raise ReleaseBlocked("SCHEDULE_RECEIPT_REQUIRED")
        return {"status": "PUBLISHED_VERIFIED", "url": url}


def dispatch(ledger: ReleaseLedger, *, post: dict, media_url: str,
             job: dict, qa: dict, evidence: dict, when: datetime,
             update_post) -> dict:
    """update_post is the connected Metricool updateScheduledPost action.

    IMPORTANT: The tool mutates a scheduled post immediately. Never retry on a
    timeout without reconciling its stable UUID in getScheduledPosts.
    """
    args = build_update(post, media_url, qa, evidence, job, when)
    claim = ledger.claim(args["uuid"], qa["sha256"])
    if not claim["claimed"]:
        return {"status": claim["status"], "duplicate_avoided": True,
                "metricool_id": claim["post_id"]}
    try:
        response = update_post(**args)
        if isinstance(response, str):
            response = json.loads(response)
        return ledger.receipt(args["uuid"], qa["sha256"], response)
    except Exception:
        ledger.uncertain(args["uuid"])
        raise
