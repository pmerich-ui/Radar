"""Privacy-minimizing, same-origin click event receiver.

Run behind an HTTPS reverse proxy with a persistent mounted DATA_DIR.
No endpoint is enabled unless DATA_DIR is configured.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = ("offer_id", "source", "campaign", "video_id")
def store_event(payload, data_dir):
    if payload.get("type") != "offer_click":
        raise ValueError("unsupported event")
    values = []
    for field in FIELDS:
        value = payload.get(field, "")
        if not isinstance(value, str) or len(value) > 64:
            raise ValueError("invalid field")
        values.append(value)
    if not values[0]:
        raise ValueError("offer_id required")
    directory = Path(data_dir)
    if not directory.is_dir():
        raise ValueError("persistent data directory missing")
    with sqlite3.connect(directory / "dealradar_events.sqlite", timeout=15) as db:
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("""CREATE TABLE IF NOT EXISTS click_events
            (id INTEGER PRIMARY KEY, offer_id TEXT NOT NULL, source TEXT,
             campaign TEXT, video_id TEXT, received_utc TEXT NOT NULL)""")
        db.execute("INSERT INTO click_events(offer_id,source,campaign,video_id,received_utc) VALUES(?,?,?,?,?)",
                   (*values, datetime.now(timezone.utc).isoformat()))
        db.commit()

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if urlsplit(self.path).path != "/api/events":
            self.send_error(404); return
        origin = self.headers.get("Origin", "")
        host = self.headers.get("Host", "")
        if origin and urlsplit(origin).netloc != host:
            self.send_error(403); return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 2048:
                self.send_error(413); return
            payload = json.loads(self.rfile.read(size))
            store_event(payload, os.environ["DATA_DIR"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            self.send_error(400); return
        self.send_response(204)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self):
        if urlsplit(self.path).path == "/health":
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

if __name__ == "__main__":
    if not os.environ.get("DATA_DIR"):
        raise SystemExit("DATA_DIR must point to a persistent mounted directory")
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), Handler).serve_forever()
