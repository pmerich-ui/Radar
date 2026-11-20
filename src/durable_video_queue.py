"""Durable fail-closed DealRadar video job queue (no publishing side effects)."""
import json
import sqlite3
import time
import uuid
from pathlib import Path

STATES = ("IDEA","SCRIPT_READY","GENERATOR_SELECTED","RENDERING","RENDERED",
"TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED","RIGHTS_VERIFIED",
"AWAITING_USER_APPROVAL","USER_APPROVED","UPLOAD_STARTED","UPLOADED",
"PUBLISHED_VERIFIED","FAILED_RETRYABLE","BLOCKED")
ORDER = STATES[:13]
REQUIRED = {"TECHNICAL_QA_PASSED":"technical_ok",
"CREATIVE_QA_PASSED":"creative_ok","RIGHTS_VERIFIED":"rights_ok",
"USER_APPROVED":"approval_ok","UPLOAD_STARTED":"approval_ok"}
class Conflict(Exception): pass

class Queue:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs(
              id TEXT PRIMARY KEY, state TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
              retries INTEGER NOT NULL DEFAULT 0, prior_state TEXT,
              technical_ok INTEGER NOT NULL DEFAULT 0,
              creative_ok INTEGER NOT NULL DEFAULT 0,
              rights_ok INTEGER NOT NULL DEFAULT 0,
              approval_ok INTEGER NOT NULL DEFAULT 0,
              publish_key TEXT UNIQUE, updated_at REAL NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS events(
              job_id TEXT, revision INTEGER, old_state TEXT, new_state TEXT,
              at REAL, PRIMARY KEY(job_id,revision))""")
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15,isolation_level=None)
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA journal_mode=WAL")
        return db
    def add(self, job_id=None):
        job_id=job_id or str(uuid.uuid4())
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO jobs(id,state,updated_at) VALUES(?,'IDEA',?)",(job_id,time.time()))
        return job_id
    def get(self, job_id):
        with self.connect() as db:
            db.row_factory=sqlite3.Row
            r=db.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
            return dict(r) if r else None
    def transition(self, job_id, expected, target, evidence=None, publish_key=None, max_retries=3):
        evidence=evidence or {}
        if target not in STATES or expected not in STATES: raise ValueError("Unknown state")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.row_factory=sqlite3.Row
            row=db.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
            if not row or row["state"]!=expected: raise Conflict("State mismatch")
            if expected=="PUBLISHED_VERIFIED": raise Conflict("Terminal state")
            if target=="FAILED_RETRYABLE":
                if row["retries"]>=max_retries: raise Conflict("Retry limit")
                prior=expected
                retries=row["retries"]+1
            elif expected=="FAILED_RETRYABLE":
                if target!=row["prior_state"]: raise Conflict("Invalid retry recovery")
                prior=None
                retries=row["retries"]
            elif target=="BLOCKED":
                prior=None; retries=row["retries"]
            else:
                if expected not in ORDER or target not in ORDER or ORDER.index(target)!=ORDER.index(expected)+1:
                    raise Conflict("Illegal transition")
                prior=None; retries=row["retries"]
            flags={k:bool(row[k]) or evidence.get(k) is True for k in
                ("technical_ok","creative_ok","rights_ok","approval_ok")}
            if target in REQUIRED and not flags[REQUIRED[target]]:
                raise Conflict("Missing verified gate evidence")
            if target in ("UPLOAD_STARTED","UPLOADED","PUBLISHED_VERIFIED") and not all(flags.values()):
                raise Conflict("Missing publication prerequisites")
            if target=="UPLOAD_STARTED" and not (publish_key or row["publish_key"]):
                raise Conflict("Missing idempotency key")
            if publish_key and row["publish_key"] and row["publish_key"]!=publish_key:
                raise Conflict("Publication key cannot change")
            db.execute("""UPDATE jobs SET state=?,revision=revision+1,retries=?,prior_state=?,
                technical_ok=?,creative_ok=?,rights_ok=?,approval_ok=?,
                publish_key=COALESCE(publish_key,?),updated_at=? WHERE id=?""",
                (target,retries,prior,*[int(flags[k]) for k in flags],
                 publish_key,time.time(),job_id))
            db.execute("INSERT INTO events VALUES(?,?,?,?,?)",
                (job_id,row["revision"]+1,expected,target,time.time()))
            db.row_factory=sqlite3.Row
            return dict(db.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone())
