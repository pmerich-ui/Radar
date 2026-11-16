import hashlib,json,os,tempfile
from pathlib import Path
from .producer import CATALOG,render
root=Path("output");root.mkdir(exist_ok=True)
p=Path("data/produced.json");p.parent.mkdir(exist_ok=True)
h=json.loads(p.read_text()) if p.exists() else {"produced":[]}
used={r["id"] for r in h["produced"]}
limit=max(1,min(5,int(os.environ.get("BATCH_SIZE","1"))))
new=[]
for item in CATALOG:
 uid=hashlib.sha256("|".join(item).encode()).hexdigest()[:24]
 if uid in used:continue
 path=root/(uid+".mp4");qa=render(item,path)
 if any(x.get("sha256")==qa["sha256"] for x in h["produced"]):raise RuntimeError("duplicate media")
 r={"id":uid,"sha256":qa["sha256"],"language":item[0],"title":item[3],"status":"LEGACY_RENDER_NOT_V5_APPROVED","technical_qa":qa,"creative_qa":"NOT_PASSED","rights_verified":False,"user_approved":False,"publishable":False};h["produced"].append(r);new.append(r)
 if len(new)>=limit:break
# Replace the manifest atomically so interrupted writes cannot truncate the queue.
# Keep the temporary file on the same filesystem as the destination.
with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=p.parent, prefix=".produced-", suffix=".tmp", delete=False) as tmp:
 tmp_path=Path(tmp.name)
 try:
  tmp.write(json.dumps(h,indent=2,ensure_ascii=False)+"\\n")
  tmp.flush()
  os.fsync(tmp.fileno())
 except BaseException:
  tmp_path.unlink(missing_ok=True)
  raise
try:
 os.replace(tmp_path,p)
except BaseException:
 tmp_path.unlink(missing_ok=True)
 raise
(root/"report.json").write_text(json.dumps({"new":len(new),"publication":"BLOCKED","reason":"Legacy illustrated zoompan renderer is not V5 photorealistic motion; creative QA and rights/user approvals missing","v5_publishable":0}))
print(json.dumps({"generated":len(new),"total":len(h["produced"])}))
