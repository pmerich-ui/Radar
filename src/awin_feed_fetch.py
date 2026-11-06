"""Secure Awin feed downloader for scheduled, read-only audits.

AWIN_FEED_URL is a GitHub Actions secret, never committed or printed.
The endpoint must be an HTTPS URL at productdata.awin.com.
No redirects, no external writes, no affiliate publication.
"""
from __future__ import annotations
import argparse
import gzip
import json
import os
from pathlib import Path
import ssl
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from .agent05_feed import run as audit_feed

MAX_COMPRESSED = 100 * 1024 * 1024
MAX_UNCOMPRESSED = 500 * 1024 * 1024
ALLOWED_HOSTS = {"productdata.awin.com"}

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def validate_url(url):
    try:
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS
                or parts.port not in (None, 443) or parts.username or parts.password
                or parts.fragment or not parts.path.startswith("/")):
            raise ValueError("AWIN_FEED_URL_INVALID")
    except (ValueError, AttributeError):
        raise ValueError("AWIN_FEED_URL_INVALID") from None
    return url

def download_and_audit(url, *, root=None, candidate_callback=None):
    url = validate_url(url)
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    target = root / "data" / "awin" / "incoming" / "scheduled.csv.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    opener = build_opener(HTTPSHandler(context=ssl.create_default_context()), NoRedirect())
    req = Request(url, headers={"User-Agent": "DealRadar-AwinFeedAudit/1.0", "Accept": "application/gzip, application/octet-stream"})
    tmp = None
    try:
        with opener.open(req, timeout=40) as response:
            if response.status != 200:
                raise ValueError("AWIN_HTTP_NOT_OK")
            with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".part", delete=False) as out:
                tmp = Path(out.name)
                size = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_COMPRESSED:
                        raise ValueError("AWIN_COMPRESSED_TOO_LARGE")
                    out.write(chunk)
        # Check gzip integrity and decompressed size before invoking the auditor.
        if not tmp or not tmp.is_file():
            raise ValueError("AWIN_EMPTY_DOWNLOAD")
        expanded = 0
        with gzip.open(tmp, "rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                expanded += len(chunk)
                if expanded > MAX_UNCOMPRESSED:
                    raise ValueError("AWIN_UNCOMPRESSED_TOO_LARGE")
        tmp.replace(target)
        result = audit_feed("data/awin/incoming/scheduled.csv.gz", root=root)
        if candidate_callback is not None and result.get("status") == "COMPLETED":
            candidate_callback(root)
        return result
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        target.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="reports/awin_feed_status.json")
    args = parser.parse_args()
    url = os.environ.get("AWIN_FEED_URL", "")
    if not url:
        result = {"status": "BLOCKED", "reason": "AWIN_FEED_URL_NOT_CONFIGURED",
                  "publishable_deals": 0, "publishing_enabled": False}
    else:
        try:
            result = download_and_audit(url)
        except Exception as exc:
            # Never print URLs, exception strings or response bodies: secrets may be embedded.
            result = {"status": "BLOCKED", "reason": "AWIN_DOWNLOAD_OR_AUDIT_FAILED",
                      "error_type": type(exc).__name__,
                      "publishable_deals": 0, "publishing_enabled": False}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "reason": result["reason"],
                      "publishable_deals": 0, "publishing_enabled": False}))
    return 0 if result["status"] == "COMPLETED" else 2

if __name__ == "__main__":
    raise SystemExit(main())
