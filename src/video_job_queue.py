"""Fail-closed SQLite queue. Database path must be on persistent storage, NOT an Actions runner."""
import json, sqlite3, time, uuid
from pathlib import Path
STATES = ("IDEA","SCRIPT_READY","GENERATOR_SELECTED","RENDERING","RENDERED","TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED","RIGHTS_VERIFIED","AWAITING_USER_APPROVAL","USER_APPROVED","UPLOAD_STARTED","UPLOADED","PUBLISHED_VERIFIED","FAILED_RETRYABLE","BLOCKED")
NEXT = dict(zip(STATES[:13], STATES[1:14]))
class Queue:
    def __init__(self, path):
        p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(p),isolation_level=None,timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,state TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 0,retries INTEGER NOT NULL DEFAULT 0,resume_state TEXT,approval_id TEXT,platform_post_id TEXT UNIQUE,payload TEXT NOT NULL,updated_at INTEGER NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS evidence(job_id TEXT NOT NULL,state TEXT NOT NULL,reference TEXT NOT NULL,PRIMARY KEY(job_id,state))")
        self.db.execute("CREATE TABLE IF NOT EXISTS events(id TEXT NOT NULL,revision INTEGER NOT NULL,from_state TEXT,to_state TEXT NOT NULL,at INTEGER NOT NULL,PRIMARY KEY(id,revision))")
    def create(self,payload,job_id=None):
        job_id=job_id or str(uuid.uuid4())
        self.db.execute("INSERT OR IGNORE INTO jobs(id,state,payload,updated_at) VALUES(?,?,?,?)",(job_id,"IDEA",json.dumps(payload),int(time.time())))
        return job_id
    def get(self,job_id):
        row=self.db.execute("SELECT id,state,revision,retries,resume_state,approval_id,platform_post_id FROM jobs WHERE id=?",(job_id,)).fetchone()
        return dict(zip(("id","state","revision","retries","resume_state","approval_id","platform_post_id"),row)) if row else None
    def transition(self,job_id,expected,target,approval_id=None,platform_post_id=None,evidence_ref=None):
        if expected not in STATES or target not in STATES: raise ValueError("Unknown state")
        if expected in ("BLOCKED","PUBLISHED_VERIFIED","FAILED_RETRYABLE"): raise ValueError("Terminal or paused state")
        if NEXT.get(expected)!=target and target not in ("FAILED_RETRYABLE","BLOCKED"): raise ValueError("Forbidden transition")
        if target in ("TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED","RIGHTS_VERIFIED") and (not isinstance(evidence_ref,str) or not evidence_ref.strip()): raise ValueError("QA or rights evidence required")
        if evidence_ref is not None and target not in ("TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED","RIGHTS_VERIFIED"): raise ValueError("Evidence only allowed for QA or rights states")
        if target=="USER_APPROVED" and not approval_id: raise ValueError("Specific approval required")
        if target=="PUBLISHED_VERIFIED" and not platform_post_id: raise ValueError("Verified post ID required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row=self.db.execute("SELECT state,revision,retries,approval_id FROM jobs WHERE id=?",(job_id,)).fetchone()
            if not row or row[0]!=expected:
                self.db.execute("ROLLBACK"); return False
            state,rev,retries,old_approval=row
            if target in ("USER_APPROVED","UPLOAD_STARTED","UPLOADED","PUBLISHED_VERIFIED"):
                proven={r[0] for r in self.db.execute("SELECT state FROM evidence WHERE job_id=?",(job_id,))}
                if not {"TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED","RIGHTS_VERIFIED"}.issubset(proven): raise ValueError("Missing QA or rights evidence")
            if expected=="USER_APPROVED" and target=="UPLOAD_STARTED" and not old_approval: raise ValueError("Approval missing")
            if target=="FAILED_RETRYABLE" and retries>=3: target="BLOCKED"
            self.db.execute("UPDATE jobs SET state=?,revision=?,retries=?,resume_state=?,approval_id=?,platform_post_id=COALESCE(?,platform_post_id),updated_at=? WHERE id=?",(target,rev+1,retries+int(target=="FAILED_RETRYABLE"),expected if target=="FAILED_RETRYABLE" else None,approval_id or old_approval,platform_post_id,int(time.time()),job_id))
            self.db.execute("INSERT INTO events VALUES(?,?,?,?,?)",(job_id,rev+1,expected,target,int(time.time())))
            if evidence_ref:
                self.db.execute("INSERT INTO evidence(job_id,state,reference) VALUES(?,?,?)",(job_id,target,evidence_ref))
            self.db.execute("COMMIT"); return True
        except Exception:
            self.db.execute("ROLLBACK"); raise
    def resume(self,job_id):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row=self.db.execute("SELECT state,resume_state,revision FROM jobs WHERE id=?",(job_id,)).fetchone()
            if not row or row[0]!="FAILED_RETRYABLE" or row[1] is None or row[1] in ("RENDERING","UPLOAD_STARTED","UPLOADED","PUBLISHED_VERIFIED"):
                self.db.execute("ROLLBACK"); return False
            state,prior,rev=row
            self.db.execute("UPDATE jobs SET state=?,resume_state=NULL,revision=?,updated_at=? WHERE id=?",(prior,rev+1,int(time.time()),job_id))
            self.db.execute("INSERT INTO events VALUES(?,?,?,?,?)",(job_id,rev+1,state,prior,int(time.time())))
            self.db.execute("COMMIT"); return True
        except Exception:
            self.db.execute("ROLLBACK"); raise
