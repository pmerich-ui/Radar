"""Persistent handoff to an authorized publishing adapter; no fabricated success."""
import sqlite3, json
from src.media_recovery_v8 import publication_ready

class PublicationBridge:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS publication (sha TEXT PRIMARY KEY, state TEXT NOT NULL, receipt TEXT)")
        self.db.commit()

    def submit(self, job, qa, evidence, adapter):
        if not publication_ready(job, qa, evidence):
            return {"state": "BLOCKED", "reason": "EVIDENCE_REQUIRED"}
        sha = qa["sha256"]
        with self.db:
            cur = self.db.execute("INSERT OR IGNORE INTO publication VALUES (?, 'UPLOAD_STARTED', NULL)", (sha,))
            claimed = cur.rowcount == 1
        if not claimed:
            state, receipt = self.db.execute("SELECT state, receipt FROM publication WHERE sha=?", (sha,)).fetchone()
            return {"state": state, "receipt": json.loads(receipt) if receipt else None}
        try:
            receipt = adapter.submit(job, sha)
            if not isinstance(receipt, dict) or not receipt.get("id"):
                raise ValueError("MISSING_RECEIPT")
        except Exception:
            # An ambiguous submission must be reconciled, never blindly repeated.
            with self.db:
                self.db.execute("UPDATE publication SET state='RECONCILE_REQUIRED' WHERE sha=?", (sha,))
            return {"state": "RECONCILE_REQUIRED"}
        with self.db:
            self.db.execute("UPDATE publication SET state='UPLOADED', receipt=? WHERE sha=?", (json.dumps(receipt), sha))
        return {"state": "UPLOADED", "receipt": receipt}
