"""Produce an 18-second vertical product-photo motion draft from licensed local photos.

Manifest example:
{"product_name":"Example product","assets":[{"path":"assets/product.jpg",
"license":"CC0-1.0","source":"https://...","evidence":"https://..."}]}
An asset's manifest claim is NOT independently verified rights evidence.
No affiliate prices, discounts, or claims are synthesized.
"""
import argparse
import json
import subprocess
from pathlib import Path

ALLOWED_EXT={".jpg",".jpeg",".png",".webp"}
def prepare(manifest, output):
    spec=json.loads(Path(manifest).read_text(encoding="utf-8"))
    assets=spec.get("assets",[])
    if len(assets)!=3:
        raise ValueError("Exactly three authorized product photos required")
    root=Path(manifest).resolve().parent
    photos=[]
    for a in assets:
        p=(root/a["path"]).resolve()
        if not p.is_relative_to(root) or not p.is_file() or p.suffix.lower() not in ALLOWED_EXT:
            raise ValueError("Missing or unsafe asset")
        if not a.get("license") or not a.get("source") or not a.get("evidence"):
            raise ValueError("Asset rights documentation incomplete")
        photos.append(p)
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y"]
    for p in photos:
        cmd += ["-loop","1","-framerate","30","-t","6","-i",str(p)]
    # Original synthesized audio; no third-party music or audio licensing.
    cmd += ["-f","lavfi","-i","sine=frequency=180:sample_rate=44100:duration=18"]
    filters=[]
    for i in range(3):
        filters.append(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0003,1.04)':d=180:s=1080x1920:fps=30,trim=duration=6,setpts=PTS-STARTPTS[v{i}]")
    filters.append("[v0][v1][v2]concat=n=3:v=1:a=0,format=yuv420p[v]")
    cmd += ["-filter_complex",";".join(filters),"-map","[v]","-map","3:a:0",
            "-t","18","-c:v","libx264","-preset","veryfast","-crf","23",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-movflags","+faststart",str(output)]
    subprocess.run(cmd,check=True,timeout=240)
    from .video_qa_agent import inspect
    result=inspect(output)
    result.update({"file":str(output),"creative_qa":"PENDING_HUMAN_REVIEW",
                   "rights":"RIGHTS_UNVERIFIED","publication_authorized":False})
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--output",default="output/product-photo-draft.mp4")
    args=p.parse_args()
    print(json.dumps(prepare(args.manifest,args.output)))
