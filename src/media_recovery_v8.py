"""Bounded media recovery and real technical QA. No publishing side effects."""
import hashlib, json, math, os, re, shutil, subprocess, time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

MAX_BYTES=150*1024*1024
HOSTS={"static.metricool.com"}
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def digest(path):
    with open(path,"rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def fetch(url,target):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname not in HOSTS or u.username or u.password or u.port not in (None,443):
        raise ValueError("UNAPPROVED_MEDIA_SOURCE")
    with build_opener(NoRedirect()).open(Request(url,headers={"User-Agent":"DealRadar-QA/1"}),timeout=20) as response:
        size=0
        with target.open("wb") as out:
            while chunk:=response.read(65536):
                size+=len(chunk)
                if size>MAX_BYTES: raise ValueError("MEDIA_TOO_LARGE")
                out.write(chunk)
        if not size: raise ValueError("EMPTY_MEDIA")

def recover(job, dest, fetcher=fetch, sleeper=time.sleep):
    dest=Path(dest); dest.parent.mkdir(parents=True,exist_ok=True)
    expected=job.get("sha256")
    attempts=[]
    sources=job.get("sources",[])
    for source in sources:
        for attempt in range(1,4):
            tmp=dest.with_suffix(".part")
            try:
                if source.get("local"):
                    # Local alternatives must be content-addressed by trusted manifest.
                    if not expected: raise ValueError("LOCAL_HASH_REQUIRED")
                    local=Path(source["local"]).resolve()
                    if not local.is_relative_to(Path("output").resolve()): raise ValueError("LOCAL_PATH_DENIED")
                    if local.stat().st_size>MAX_BYTES: raise ValueError("MEDIA_TOO_LARGE")
                    shutil.copyfile(local,tmp)
                else:
                    fetcher(source["url"],tmp)
                actual=digest(tmp)
                if expected and actual!=expected: raise ValueError("HASH_MISMATCH")
                tmp.replace(dest)
                return {"status":"RENDERED","sha256":actual,"attempts":attempts,"source":source.get("url","local")}
            except (OSError,ValueError,KeyError) as exc:
                attempts.append({"attempt":attempt,"error":type(exc).__name__})
                tmp.unlink(missing_ok=True)
                if attempt<3: sleeper(attempt*2)
    return {"status":"FAILED_RETRYABLE","attempts":attempts}

def run(args,timeout=90):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)

def inspect(path):
    try:
        raw=run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)])
        obj=json.loads(raw.stdout)
        v=next(s for s in obj["streams"] if s["codec_type"]=="video")
        a=next(s for s in obj["streams"] if s["codec_type"]=="audio")
        dur=float(obj["format"]["duration"])
        n,d=map(int,v["r_frame_rate"].split("/"))
        if not (math.isfinite(dur) and 15<=dur<=20 and (v["width"],v["height"])==(1080,1920) and v["codec_name"]=="h264" and v["pix_fmt"]=="yuv420p" and 23<=n/d<=60 and a["codec_name"]=="aac" and float(a.get("duration") or dur)>=dur-0.5):
            return {"status":"BLOCKED","reason":"SPEC_MISMATCH","duration":dur}
        run(["ffmpeg","-nostdin","-v","error","-xerror","-i",str(path),"-map","0:v:0","-map","0:a:0","-f","null","-"])
        vol=run(["ffmpeg","-nostdin","-hide_banner","-i",str(path),"-map","0:a:0","-af","volumedetect","-vn","-f","null","-"]).stderr
        match=re.search(r"mean_volume:\s*(-?[\d.]+) dB",vol)
        if not match or float(match[1]) < -35:
            return {"status":"BLOCKED","reason":"AUDIO_SILENT_OR_TOO_QUIET"}
        return {"status":"TECHNICAL_QA_PASSED","duration":dur,"mean_db":float(match[1]),"sha256":digest(path),"creative_review_required":True}
    except (OSError,ValueError,KeyError,StopIteration,ZeroDivisionError,subprocess.SubprocessError):
        return {"status":"BLOCKED","reason":"PROBE_OR_DECODE_FAILED"}

def publication_ready(job,qa,evidence):
    # Evidence is supplied separately by the authorized reviewer; never inferred from QA.
    return (qa.get("status")=="TECHNICAL_QA_PASSED"
            and bool(qa.get("sha256")) and evidence.get("sha256")==qa.get("sha256")
            and evidence.get("rights_verified") is True and bool(evidence.get("rights_source"))
            and evidence.get("facts_verified") is True and evidence.get("disclosure_verified") is True
            and (not job.get("affiliate") or all(evidence.get(k) is True for k in ("merchant_approved","tracking_tested","swiss_delivery_verified","price_verified")))
            and isinstance(evidence.get("creative_score"),(int,float)) and 85<=evidence["creative_score"]<=100
            and evidence.get("reviewer") and evidence.get("brand_id")==7820933
            and evidence.get("handle")=="dy3ko4nveu0o")

def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--manifest",default="config/media_recovery_v8.json");p.add_argument("--output",default="recovery-output")
    args=p.parse_args(); root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    results=[]
    for job in json.loads(Path(args.manifest).read_text())["jobs"]:
        uid=job["id"]
        if not re.fullmatch(r"[a-z0-9-]+",uid): raise ValueError("INVALID_JOB_ID")
        path=root/(uid+".mp4")
        result=recover(job,path)
        if result["status"]=="RENDERED":
            result["qa"]=inspect(path)
            # Review frames are evidence, not automatic creative approval.
            if result["qa"]["status"]=="TECHNICAL_QA_PASSED":
                try: run(["ffmpeg","-nostdin","-y","-v","error","-i",str(path),"-vf","fps=1/3,scale=270:480,tile=3x3","-frames:v","1",str(root/(uid+"-review.jpg"))])
                except subprocess.SubprocessError: result["review_frames"]="FAILED"
        result.update({"id":uid,"publication":"NOT_ATTEMPTED","rights":"UNVERIFIED"})
        results.append(result)
    target=root/"report.json"; tmp=target.with_suffix(".tmp")
    tmp.write_text(json.dumps({"jobs":results},indent=2));tmp.replace(target)
    print(target.read_text())
if __name__=="__main__": main()
