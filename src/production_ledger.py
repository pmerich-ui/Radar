"""Durable, fail-closed per-video production ledger. No network or publishing effects."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

STATES = ("IDEA", "SCRIPT_READY", "GENERATOR_SELECTED", "RENDERING",
          "RENDERED", "TECHNICAL_QA_PASSED", "CREATIVE_QA_PASSED",
          "RIGHTS_VERIFIED", "AWAITING_USER_APPROVAL", "USER_APPROVED",
          "UPLOAD_STARTED", "UPLOADED", "PUBLISHED_VERIFIED",
          "FAILED_RETRYABLE", "BLOCKED")
NEXT = dict(zip(STATES[:12], STATES[1:13]))
# Retrying never skips a quality or approval gate.
RETRY_TO = {"FAILED_RETRYABLE": "GENERATOR_SELECTED"}

def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30, isolation_level=None)
    db.execute("PRAGMA busy_timeout=30000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, state TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0,
        sha256 TEXT, metricool_id TEXT UNIQUE, tiktok_id TEXT UNIQUE,
        tiktok_url TEXT, evidence TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
        old_state TEXT, new_state TEXT NOT NULL, evidence TEXT NOT NULL,
        created_at TEXT NOT NULL)""")
    return db

def close(db):
    """Explicitly release database resources after each job."""
    db.close()


def now():
    return datetime.now(timezone.utc).isoformat()

def create(db, job_id, brief):
    if not isinstance(job_id, str) or not job_id or len(job_id) > 100:
        raise ValueError("Invalid job id")
    if not isinstance(brief, dict) or not brief:
        raise ValueError("Nonempty brief required")
    stamp = now()
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute("INSERT INTO jobs(id,state,evidence,updated_at) VALUES (?,?,?,?)",
                   (job_id, "IDEA", json.dumps({"brief": brief}), stamp))
        db.execute("INSERT INTO events(job_id,old_state,new_state,evidence,created_at) VALUES (?,?,?,?,?)",
                   (job_id, None, "IDEA", json.dumps(brief), stamp))
        db.commit()
    except BaseException:
        db.rollback()
        raise

def transition(db, job_id, target, evidence=None):
    if target not in STATES:
        raise ValueError("Unknown state")
    evidence = evidence or {}
    if not isinstance(evidence, dict):
        raise ValueError("Evidence must be an object")
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT state,sha256,metricool_id,tiktok_id,evidence FROM jobs WHERE id=?",
                         (job_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown job")
        state, digest, metricool, tiktok, prior = row
        if state == target:
            db.commit()
            return False  # idempotent retry, no second external action
        allowed = target == NEXT.get(state) or target in ("FAILED_RETRYABLE", "BLOCKED") and state != "PUBLISHED_VERIFIED" or RETRY_TO.get(state) == target
        if target == "FAILED_RETRYABLE":
            if state in ("UPLOAD_STARTED", "UPLOADED"):
                raise ValueError("Upload outcome uncertain: reconcile externally; never retry upload automatically")
            retries = db.execute("SELECT COUNT(*) FROM events WHERE job_id=? AND new_state='FAILED_RETRYABLE'", (job_id,)).fetchone()[0]
            if retries >= 3:
                raise ValueError("Retry budget exhausted; manual reconciliation required")
        if not allowed:
            raise ValueError("Invalid state transition: " + state + " -> " + target)
        if target == "RENDERED":
            path = Path(evidence.get("mp4_path", ""))
            if not path.is_file() or path.suffix.lower() != ".mp4":
                raise ValueError("MP4 file evidence required")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if evidence.get("sha256") != actual:
                raise ValueError("MP4 hash mismatch")
            digest = actual
        if target == "TECHNICAL_QA_PASSED" and evidence.get("technical_pass") is not True:
            raise ValueError("Technical QA evidence missing")
        if target == "CREATIVE_QA_PASSED" and (type(evidence.get("score")) is not int or evidence["score"] < 85 or not evidence.get("reviewer")):
            raise ValueError("Independent creative QA evidence missing")
        if target == "RIGHTS_VERIFIED" and (evidence.get("commercial_rights") is not True or not evidence.get("license_reference")):
            raise ValueError("Commercial license evidence missing")
        if target == "USER_APPROVED" and (evidence.get("approved_sha256") != digest or not evidence.get("approval_reference")):
            raise ValueError("File-specific owner approval required")
        if target == "UPLOADED":
            metricool = evidence.get("metricool_id")
            if not metricool or not isinstance(metricool, str):
                raise ValueError("Metricool post ID required")
        if target == "PUBLISHED_VERIFIED":
            tiktok = evidence.get("tiktok_id")
            url = evidence.get("tiktok_url")
            if not tiktok or not isinstance(tiktok, str) or not isinstance(url, str) or not url.startswith("https://www.tiktok.com/") or evidence.get("platform_confirmed") is not True:
                raise ValueError("Verified TikTok ID, URL and platform confirmation required")
        merged = json.loads(prior)
        merged[target] = evidence
        stamp = now()
        db.execute("""UPDATE jobs SET state=?,version=version+1,sha256=?,metricool_id=?,
                   tiktok_id=?,tiktok_url=?,evidence=?,updated_at=? WHERE id=?""",
                   (target,digest,metricool,tiktok,evidence.get("tiktok_url") if target=="PUBLISHED_VERIFIED" else None,
                    json.dumps(merged),stamp,job_id))
        db.execute("INSERT INTO events(job_id,old_state,new_state,evidence,created_at) VALUES (?,?,?,?,?)",
                   (job_id,state,target,json.dumps(evidence),stamp))
        db.commit()
        return True
    except BaseException:
        db.rollback()
        raise

def status(db, job_id):
    row = db.execute("SELECT id,state,version,sha256,metricool_id,tiktok_id,tiktok_url FROM jobs WHERE id=?", (job_id,)).fetchone()
    return dict(zip(("id","state","version","sha256","metricool_id","tiktok_id","tiktok_url"),row)) if row else None
