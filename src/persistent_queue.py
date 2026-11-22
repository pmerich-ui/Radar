"""Durable idempotent DealRadar job ledger; keep database on a persistent volume.

A runner's temporary SQLite file is NOT persistent across GitHub Actions runs.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

STATES=("IDEA","SCRIPT_READY","GENERATOR_SELECTED","RENDERING","RENDERED",
"TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED","RIGHTS_VERIFIED",
"AWAITING_USER_APPROVAL","USER_APPROVED","UPLOAD_STARTED","UPLOADED",
"PUBLISHED_VERIFIED","FAILED_RETRYABLE","BLOCKED")
# Only the normal production sequence is eligible for advance(); terminal states are never advanced.
NEXT={a:b for a,b in zip(STATES[:12],STATES[1:13])}
MAX_RETRIES=3

class Queue:
    def __init__(self, db):
        self.path=Path(db)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=30,isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs(
          id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL,
          status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
          media_hash TEXT UNIQUE, external_post_id TEXT UNIQUE,
          approval_ref TEXT, last_error TEXT)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS job_evidence(
          job_id TEXT NOT NULL, state TEXT NOT NULL, evidence_ref TEXT NOT NULL,
          PRIMARY KEY(job_id,state), FOREIGN KEY(job_id) REFERENCES jobs(id))""")
    def close(self): self.db.close()
    def add(self, key, payload):
        fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        job_id=hashlib.sha256(str(key).encode()).hexdigest()[:24]
        self.db.execute("INSERT OR IGNORE INTO jobs(id,fingerprint,status) VALUES(?,?,'IDEA')",(job_id,fingerprint))
        job=self.get(job_id)
        if job is None or job["fingerprint"] != fingerprint:
            raise ValueError("Campaign key or payload fingerprint collision")
        return job
    def get(self, job_id):
        row=self.db.execute("SELECT id,fingerprint,status,attempts,media_hash,external_post_id,approval_ref,last_error FROM jobs WHERE id=?",(job_id,)).fetchone()
        return dict(zip(("id","fingerprint","status","attempts","media_hash","external_post_id","approval_ref","last_error"),row)) if row else None
    def advance(self, job_id, expected, target, *, media_hash=None, approval_ref=None, external_post_id=None, evidence_ref=None):
        if expected not in STATES or target not in STATES:
            raise ValueError("Unknown state")
        if NEXT.get(expected)!=target:
            raise ValueError("Illegal transition")
        if target in ("TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED","RIGHTS_VERIFIED","PUBLISHED_VERIFIED") and not evidence_ref:
            raise ValueError("Independent QA, rights or publication evidence required")
        if target=="USER_APPROVED" and not approval_ref:
            raise ValueError("Specific user approval evidence required")
        if target=="UPLOADED" and not external_post_id:
            raise ValueError("Upload confirmation required")
        if target=="RENDERED" and not media_hash:
            raise ValueError("Media fingerprint required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            current=self.get(job_id)
            if not current or current["status"]!=expected:
                self.db.execute("ROLLBACK")
                return False
            if target in ("USER_APPROVED", "UPLOAD_STARTED", "UPLOADED", "PUBLISHED_VERIFIED"):
                required = ("TECHNICAL_QA_PASSED", "CREATIVE_QA_PASSED", "RIGHTS_VERIFIED")
                proven = {row[0] for row in self.db.execute(
                    "SELECT state FROM job_evidence WHERE job_id=?", (job_id,)).fetchall()}
                if not set(required).issubset(proven) or not current["media_hash"]:
                    raise ValueError("Upload gate: missing media fingerprint or QA/rights evidence")
                if target != "USER_APPROVED" and not current["approval_ref"]:
                    raise ValueError("Upload gate: missing specific user approval")
            self.db.execute("""UPDATE jobs SET status=?,media_hash=COALESCE(?,media_hash),
                approval_ref=COALESCE(?,approval_ref),
                external_post_id=COALESCE(?,external_post_id) WHERE id=?""",
                (target,media_hash,approval_ref,external_post_id,job_id))
            if evidence_ref:
                self.db.execute("INSERT INTO job_evidence(job_id,state,evidence_ref) VALUES(?,?,?)",
                                (job_id,target,evidence_ref))
            self.db.execute("COMMIT")
            return True
        except Exception:
            self.db.execute("ROLLBACK")
            raise
    def fail(self, job_id, expected, error):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            current=self.get(job_id)
            if not current or current["status"]!=expected or expected in ("PUBLISHED_VERIFIED","UPLOADED","UPLOAD_STARTED"):
                self.db.execute("ROLLBACK")
                return False
            attempts=current["attempts"]+1
            status="BLOCKED" if attempts>=MAX_RETRIES else "FAILED_RETRYABLE"
            self.db.execute("UPDATE jobs SET attempts=?,status=?,last_error=? WHERE id=?",
                            (attempts,status,str(error)[:500],job_id))
            self.db.execute("COMMIT")
            return True
        except Exception:
            self.db.execute("ROLLBACK")
            raise
    def resume(self, job_id):
        # Do not retry a potentially charged upload; manual reconciliation required.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            current=self.get(job_id)
            if not current or current["status"]!="FAILED_RETRYABLE" or current["attempts"]>=MAX_RETRIES:
                self.db.execute("ROLLBACK")
                return False
            self.db.execute("UPDATE jobs SET status='IDEA' WHERE id=?",(job_id,))
            self.db.execute("COMMIT")
            return True
        except Exception:
            self.db.execute("ROLLBACK")
            raise
