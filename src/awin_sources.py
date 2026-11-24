"""Authenticated, bounded Awin feed cache. Never authorizes publication."""
import csv
import gzip
import hashlib
import io
import json
import os
import re
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit
from cryptography.fernet import Fernet, InvalidToken
from . import awin_feed_fetch as aff

MAX_COMPRESSED = 100 * 1024 * 1024
MAX_UNCOMPRESSED = 500 * 1024 * 1024
MAX_AGE = 7 * 86400
REQUIRED = {"aw_product_id", "product_name", "aw_deep_link", "merchant_id"}

class FeedError(Exception):
    pass

def check_url(url):
    try:
        if not isinstance(url, str) or any(ord(c) <= 32 or ord(c) == 127 for c in url):
            raise ValueError()
        p = urlsplit(url)
        if (p.scheme != "https" or p.hostname != "productdata.awin.com"
            or p.port not in (None, 443) or p.username is not None
            or p.password is not None or p.fragment or not p.path.startswith("/")
            or aff.validate_url(url) is False):
            raise ValueError()
    except Exception:
        raise FeedError("URL abgelehnt") from None

def redact(text):
    for name in ("AWIN_FEED_APIKEY", "AWIN_API_TOKEN", "AWIN_CACHE_KEY", "AWIN_FEED_URL"):
        value = os.getenv(name)
        if value:
            text = text.replace(value, "***")
    return re.sub(r"https?://[^\s]+", "***", text)

def inspect_gzip(data):
    if len(data) > MAX_COMPRESSED:
        raise FeedError("Download zu gross")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
            total = 0
            while chunk := gz.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UNCOMPRESSED:
                    raise FeedError("entpackt zu gross")
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
            reader = csv.DictReader(io.TextIOWrapper(gz, encoding="utf-8-sig", newline=""))
            if not REQUIRED.issubset(reader.fieldnames or []):
                raise FeedError("Pflichtspalten fehlen")
            count = sum(1 for row in reader if row.get("aw_product_id") and row.get("merchant_id"))
            if not count:
                raise FeedError("Feed leer")
            return count
    except (OSError, EOFError, UnicodeError, csv.Error):
        raise FeedError("Feed ungueltig") from None

class Cache:
    def __init__(self, directory, fernet):
        self.dir = Path(directory)
        self.fernet = fernet
        self.now = time.time

    @classmethod
    def from_env(cls):
        try:
            key = os.getenv("AWIN_CACHE_KEY")
            return cls("data/awin_cache", Fernet(key.encode()) if key else None)
        except ValueError:
            raise FeedError("Cache-Schluessel ungueltig") from None

    def path(self, feed_id):
        if not isinstance(feed_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", feed_id):
            raise FeedError("Feed-ID ungueltig")
        return self.dir / (feed_id + ".enc")

    def put(self, feed_id, data):
        path = self.path(feed_id)
        inspect_gzip(data)
        if not self.fernet:
            raise FeedError("kein Cache-Schluessel")
        header = json.dumps({"id": feed_id, "time": self.now(), "sha": hashlib.sha256(data).hexdigest()}).encode()
        token = self.fernet.encrypt(header + b"\n" + data)
        self.dir.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.dir, delete=False) as f:
                temp = Path(f.name)
                f.write(token)
            os.replace(temp, path)
        finally:
            if temp:
                temp.unlink(missing_ok=True)

    def get(self, feed_id):
        if not self.fernet:
            raise FeedError("kein Cache-Schluessel")
        try:
            path = self.path(feed_id)
            if path.is_symlink() or path.stat().st_size > MAX_COMPRESSED * 2:
                raise FeedError("Cache ungueltig")
            header, data = self.fernet.decrypt(path.read_bytes()).split(b"\n", 1)
            meta = json.loads(header)
            age = self.now() - meta["time"]
            if not 0 <= age <= MAX_AGE:
                raise FeedError("Cache zu alt")
            if meta["id"] != feed_id or meta["sha"] != hashlib.sha256(data).hexdigest():
                raise FeedError("Cache manipuliert")
            inspect_gzip(data)
            return data, meta
        except (InvalidToken, OSError, ValueError, KeyError, TypeError):
            raise FeedError("Cache manipuliert oder fehlt") from None

def fetch_live(feed, cache, root):
    check_url(feed["url"])
    root = Path(root).resolve()
    captured = []
    def cb(callback_root):
        if Path(callback_root).resolve() != root:
            raise FeedError("Callback ungueltig")
        path = root / "data/awin/incoming/scheduled.csv.gz"
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise FeedError("Dateipfad ungueltig")
        with path.open("rb") as f:
            data = f.read(MAX_COMPRESSED + 1)
        inspect_gzip(data)
        captured.append(data)
    try:
        result = aff.download_and_audit(feed["url"], root=root, candidate_callback=cb)
    except Exception as e:
        raise FeedError(type(e).__name__) from None
    if result.get("status") != "COMPLETED" or len(captured) != 1:
        raise FeedError("Audit oder Callback fehlgeschlagen")
    cache.put(feed["feed_id"], captured[0])

def iter_allowed_rows(data, joined):
    if not joined:
        return
    inspect_gzip(data)
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
        for row in csv.DictReader(io.TextIOWrapper(gz, encoding="utf-8-sig", newline="")):
            if row.get("merchant_id") in joined:
                yield row

def iter_products(cache, result):
    if not result.joined:
        return
    for feed_id, status in result.feeds.items():
        if status["tier"] not in ("live", "cache"):
            continue
        data, _ = cache.get(feed_id)
        for row in iter_allowed_rows(data, result.joined):
            try:
                p = urlsplit(row["aw_deep_link"])
                if p.scheme != "https" or p.hostname not in {"awin1.com", "www.awin1.com"} or p.username is not None or p.password is not None or p.port not in (None, 443):
                    continue
            except ValueError:
                continue
            row["product_name"] = "".join(c for c in row["product_name"] if c.isprintable())[:300]
            row["needs_price_verification"] = True
            yield row

from dataclasses import dataclass, field
@dataclass
class Result:
    feeds: dict = field(default_factory=dict)
    joined: set = field(default_factory=set)
    errors: list = field(default_factory=list)
    @property
    def tier(self):
        t = {f["tier"] for f in self.feeds.values()}
        if t == {"live"}: return "live"
        if t == {"cache"}: return "cache"
        if t == {"live", "cache"}: return "mixed"
        if "missing" in t and t & {"live", "cache"}: return "degraded"
        return "deeplink_only"
