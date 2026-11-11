#!/usr/bin/env python3
"""Fail-closed, idempotent publication decision. No network calls or publishing."""
import json, hashlib, sys
from pathlib import Path

REQUIRED=("technical_pass","visual_qa_score","commercial_rights_verified",
          "advertising_claims_verified","ai_disclosure_ready","explicit_user_approval")
def decide(job, ledger):
    key=job.get("job_id")
    if not isinstance(key,str) or not key.strip(): return {"allowed":False,"reason":"missing_job_id"}
    if key in ledger.get("published_jobs",{}): return {"allowed":False,"reason":"already_published","url":ledger["published_jobs"][key]}
    if key in ledger.get("upload_attempts",{}): return {"allowed":False,"reason":"upload_attempt_already_recorded_manual_reconciliation_required"}
    for name in REQUIRED:
        value=job.get(name)
        if name=="visual_qa_score":
            if not isinstance(value,(int,float)) or isinstance(value,bool) or not 85<=value<=100:
                return {"allowed":False,"reason":"visual_qa_below_threshold_or_missing"}
        elif value is not True:
            return {"allowed":False,"reason":"missing_"+name}
    path=job.get("video_path")
    expected=job.get("sha256")
    if not isinstance(path,str) or not Path(path).is_file() or not isinstance(expected,str):
        return {"allowed":False,"reason":"missing_verified_video"}
    actual=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if actual!=expected: return {"allowed":False,"reason":"video_hash_mismatch"}
    if job.get("technical_report",{}).get("status")!="TECHNICAL_PASS":
        return {"allowed":False,"reason":"technical_report_not_passed"}
    return {"allowed":True,"reason":"eligible_for_manual_publish_handoff_only","sha256":actual}

if __name__=="__main__":
    if len(sys.argv)!=3:
        print("Usage: python3 scripts/publication_gate.py job.json ledger.json",file=sys.stderr)
        sys.exit(2)
    decision=decide(json.loads(Path(sys.argv[1]).read_text()),json.loads(Path(sys.argv[2]).read_text()))
    print(json.dumps(decision,indent=2))
    sys.exit(0 if decision["allowed"] else 1)
