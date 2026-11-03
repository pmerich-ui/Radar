"""Optional durable upload. No external requests without explicit secrets."""
import hashlib,json,os,time,urllib.request,urllib.error
from pathlib import Path

def _request(url,method,key,data=None,headers=None):
    h={"apikey":key,"Authorization":"Bearer "+key,**(headers or {})}
    req=urllib.request.Request(url,data=data,headers=h,method=method)
    with urllib.request.urlopen(req,timeout=45) as resp:return resp.status,resp.read()

def publish_to_storage(root=Path("output")):
    url=os.getenv("SUPABASE_URL","").rstrip("/")
    key=os.getenv("SUPABASE_SERVICE_ROLE_KEY","")
    bucket=os.getenv("SUPABASE_VIDEO_BUCKET","dealradar-videos")
    if not url or not key:
        print(json.dumps({"storage":"SKIPPED","reason":"Supabase secrets not configured"}))
        return
    report_path=root/"report.json"
    if not report_path.exists():raise RuntimeError("missing generation report")
    manifest=json.loads(Path("data/produced.json").read_text())
    uploaded=[]
    for row in manifest["produced"]:
        uid=row["id"];path=root/(uid+".mp4")
        if not path.exists():continue
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=row["sha256"]:raise RuntimeError("hash mismatch")
        storage_url=url+"/storage/v1/object/"+bucket+"/"+uid+".mp4"
        try:
            status,_=_request(storage_url,"POST",key,data,{"Content-Type":"video/mp4","x-upsert":"false"})
        except urllib.error.HTTPError as e:
            # Existing object is not evidence of correct content: fail closed.
            raise RuntimeError("Storage upload refused (HTTP %d); manual reconciliation required"%e.code)
        if status not in (200,201):raise RuntimeError("Storage upload not confirmed")
        uploaded.append({"id":uid,"storage_path":bucket+"/"+uid+".mp4","sha256":row["sha256"],"status":"UPLOADED_NOT_PUBLISHED"})
    (root/"storage_report.json").write_text(json.dumps(uploaded,indent=2))
    print(json.dumps({"storage":"UPLOADED","count":len(uploaded),"publishing":"DISABLED"}))

if __name__=="__main__":publish_to_storage()
