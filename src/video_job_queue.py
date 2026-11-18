"""Durable fail-closed video job state machine. No publishing or paid actions."""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

STATES = ("IDEA", "SCRIPT_READY", "GENERATOR_SELECTED", "RENDERING",
          "RENDERED", "TECHNICAL_QA_PASSED", "CREATIVE_QA_PASSED",
          "RIGHTS_VERIFIED", "AWAITING_USER_APPROVAL", "USER_APPROVED",
          "UPLOAD_STARTED", "UPLOADED", "PUBLISHED_VERIFIED",
          "FAILED_RETRYABLE", "BLOCKED")
NEXT = {a: b for a, b in zip(STATES[:13], STATES[1:13])}
# All transitions are guarded by the expected current state, inside BEGIN IMMEDIATE.
def now():
    return datetime.now(timezone.utc).isoformat()

class VideoQueue:
    def __init__(self, path):
        self.path = str(path)
        self.db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.db.execute("PRAGMA busy_timeout=30000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            payload TEXT NOT NULL, evidence TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL, upload_key TEXT UNIQUE)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
            old_state TEXT, new_state TEXT NOT NULL, at TEXT NOT NULL,
            evidence TEXT NOT NULL)""")

    def create(self, payload, job_id=None):
        job_id = job_id or str(uuid.uuid4())
        if not isinstance(payload, dict) or not job_id or len(job_id) > 128:
            raise ValueError("Invalid job")
        with self.db:
            self.db.execute("INSERT INTO jobs(id,state,payload,updated_at) VALUES (?,?,?,?)",
                            (job_id, "IDEA", json.dumps(payload), now()))
            self.db.execute("INSERT INTO events(job_id,old_state,new_state,at,evidence) VALUES (?,?,?,?,?)",
                            (job_id, None, "IDEA", now(), "{}"))
        return job_id

    def get(self, job_id):
        row = self.db.execute("SELECT id,state,attempts,payload,evidence,upload_key FROM jobs WHERE id=?", (job_id,)).fetchone()
        return None if row is None else dict(zip(("id","state","attempts","payload","evidence","upload_key"), row))

    def transition(self, job_id, expected, target, evidence=None, upload_key=None, max_retries=3):
        if expected not in STATES or target not in STATES:
            raise ValueError("Unknown state")
        evidence = evidence or {}
        if not isinstance(evidence, dict):
            raise ValueError("Evidence must be object")
        if target not in (NEXT.get(expected), "BLOCKED", "FAILED_RETRYABLE"):
            if not (expected == "FAILED_RETRYABLE" and target == "GENERATOR_SELECTED"):
                raise ValueError("Illegal transition")
        if target == "TECHNICAL_QA_PASSED" and not evidence.get("ffprobe_passed"):
            raise ValueError("Missing technical QA evidence")
        if target == "CREATIVE_QA_PASSED" and (evidence.get("creative_score", -1) < 85 or not evidence.get("human_reviewed")):
            raise ValueError("Missing creative QA evidence")
        if target == "RIGHTS_VERIFIED" and not evidence.get("commercial_rights_evidence"):
            raise ValueError("Rights unverified")
        if target == "USER_APPROVED" and not evidence.get("explicit_user_approval"):
            raise ValueError("Missing per-video approval")
        if target == "UPLOAD_STARTED" and not upload_key:
            raise ValueError("Missing idempotency upload key")
        if target == "PUBLISHED_VERIFIED" and not evidence.get("public_tiktok_url"):
            raise ValueError("Missing public URL")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute("SELECT state,attempts,upload_key FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None or row[0] != expected:
                self.db.execute("ROLLBACK")
                return False
            attempts = row[1] + (target == "FAILED_RETRYABLE")
            if attempts > max_retries:
                target = "BLOCKED"
                evidence = {"reason": "RETRY_LIMIT"}
            if expected == "UPLOAD_STARTED" and target == "FAILED_RETRYABLE":
                # Unknown upload outcome must never be retried automatically.
                target = "BLOCKED"
                evidence = {"reason": "UPLOAD_OUTCOME_UNCERTAIN"}
            self.db.execute("UPDATE jobs SET state=?,attempts=?,evidence=?,updated_at=?,upload_key=COALESCE(?,upload_key) WHERE id=?",
                            (target, attempts, json.dumps(evidence), now(), upload_key, job_id))
            self.db.execute("INSERT INTO events(job_id,old_state,new_state,at,evidence) VALUES (?,?,?,?,?)",
                            (job_id, expected, target, now(), json.dumps(evidence)))
            self.db.execute("COMMIT")
            return True
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def close(self):
        self.db.close()
