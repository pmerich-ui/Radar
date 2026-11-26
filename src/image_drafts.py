"""Offline editorial image drafts; never claim verified product advertising."""
import hashlib
import json
from pathlib import Path
from PIL import Image
from .producer import CATALOG, slide

def run(root, limit=5):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for item in [x for x in CATALOG if x[0] == "de"][:max(1,min(5,limit))]:
        digest = hashlib.sha256(("image-v1|"+"|".join(item)).encode()).hexdigest()
        path = root / (digest[:24]+".png")
        slide(item, 0, int(digest[:8],16), path)
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            if im.size != (1080,1920):
                raise ValueError("Invalid dimensions")
        results.append({"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"publishable":False,"reason":"EDITORIAL_DRAFT_REQUIRES_REVIEW"})
    (root/"report.json").write_text(json.dumps({"drafts":results,"publication_attempted":False},indent=2))
    return results

if __name__ == "__main__":
    print(json.dumps({"draft_count":len(run("output/images")),"publishable":False}))
