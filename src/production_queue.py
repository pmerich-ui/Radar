"""Durable local SQLite production queue. Requires a persistent mounted database path."""
import os
import sqlite3
import time
import uuid

STATES = ("IDEA","SCRIPT_READY","GENERATOR_SELECTED","RENDERING","RENDERED",
          "TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED","RIGHTS_VERIFIED",
          "AWAITING_USER_APPROVAL","USER_APPROVED","UPLOAD_STARTED",
          "UPLOADED","PUBLISHED_VERIFIED","FAILED_RETRYABLE","BLOCKED")
NEXT = dict(zip(STATES[:12], STATES[1:13]))
NEXT["FAILED_RETRYABLE"] = "GENERATOR_SELECTED"
MAX_RETRIES = 3

class Queue:
    def __init__(self, path):
        if path == ":memory:":
            raise ValueError("Persistent database file required")
        self.path = path
        self.db = sqlite3.connect(path, timeout=30, isolation_level=None)
        self.db.execute("PRAGMA busy_timeout=30000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs(
            id TEXT PRIMARY KEY, state TEXT NOT NULL, retries INTEGER NOT NULL DEFAULT 0,
            lease_until INTEGER NOT NULL DEFAULT 0, approval_id TEXT,
            rights_verified INTEGER NOT NULL DEFAULT 0, technical_pass INTEGER NOT NULL DEFAULT 0,
            creative_score INTEGER, upload_key TEXT UNIQUE, published_url TEXT,
            updated_at INTEGER NOT NULL)""")
    def add(self, job_id=None):
        job_id = job_id or str(uuid.uuid4())
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO jobs(id,state,updated_at) VALUES(?,?,?)",
                            (job_id,"IDEA",int(time.time())))
        return job_id
    def get(self, job_id):
        self.db.row_factory = sqlite3.Row
        row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None
    def transition(self, job_id, expected, target, *, technical=False, score=None,
                   rights=False, approval_id=None, upload_key=None, published_url=None):
        if expected not in STATES or target not in STATES:
            raise ValueError("Invalid state")
        if target != NEXT.get(expected) and target not in ("FAILED_RETRYABLE","BLOCKED"):
            raise ValueError("Illegal transition")
        if target == "TECHNICAL_QA_PASSED" and not technical:
            raise ValueError("Technical QA evidence required")
        if target == "CREATIVE_QA_PASSED" and (score is None or score < 85):
            raise ValueError("Creative QA >=85 required")
        if target == "RIGHTS_VERIFIED" and not rights:
            raise ValueError("Commercial rights evidence required")
        if target == "USER_APPROVED" and not approval_id:
            raise ValueError("Specific user approval required")
        if target == "UPLOAD_STARTED" and not upload_key:
            raise ValueError("Idempotency key required")
        if target == "PUBLISHED_VERIFIED" and not published_url:
            raise ValueError("Verified publication URL required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row=self.get(job_id)
            if not row or row["state"] != expected:
                self.db.execute("ROLLBACK"); return False
            if target == "UPLOAD_STARTED" and not (row["technical_pass"] and
                    row["creative_score"] is not None and row["creative_score"] >= 85 and
                    row["rights_verified"] and row["approval_id"]):
                raise ValueError("Publication gates not satisfied")
            retries=row["retries"]+(target=="FAILED_RETRYABLE")
            if retries > MAX_RETRIES:
                target="BLOCKED"
            self.db.execute("""UPDATE jobs SET state=?,retries=?,technical_pass=?,
                creative_score=?,rights_verified=?,approval_id=?,upload_key=?,
                published_url=?,updated_at=? WHERE id=?""",
                (target,retries,int(technical or row["technical_pass"]),
                 score if score is not None else row["creative_score"],
                 int(rights or row["rights_verified"]),approval_id or row["approval_id"],
                 upload_key or row["upload_key"],published_url or row["published_url"],
                 int(time.time()),job_id))
            self.db.execute("COMMIT"); return True
        except BaseException:
            self.db.execute("ROLLBACK"); raise
    def claim(self, job_id, *, seconds=300):
        now=int(time.time())
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row=self.get(job_id)
            if not row or row["lease_until"] > now or row["state"] in (
                    "UPLOAD_STARTED","UPLOADED","PUBLISHED_VERIFIED","BLOCKED"):
                self.db.execute("ROLLBACK"); return False
            self.db.execute("UPDATE jobs SET lease_until=? WHERE id=?",
                            (now+seconds,job_id))
            self.db.execute("COMMIT"); return True
        except BaseException:
            self.db.execute("ROLLBACK"); raise
    def release(self, job_id):
        self.db.execute("UPDATE jobs SET lease_until=0 WHERE id=?", (job_id,))
