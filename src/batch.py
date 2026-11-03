import hashlib,json,os
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
 r={"id":uid,"sha256":qa["sha256"],"language":item[0],"title":item[3]};h["produced"].append(r);new.append(r)
 if len(new)>=limit:break
p.write_text(json.dumps(h,indent=2,ensure_ascii=False)+"\n")
(root/"report.json").write_text(json.dumps({"new":len(new),"publication":"NOT_CONFIGURED"}))
print(json.dumps({"generated":len(new),"total":len(h["produced"])}))
