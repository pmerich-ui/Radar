#!/usr/bin/env python3
"""DealRadar V5: fail-closed technical video preflight. No publishing."""
import json, subprocess, sys
from pathlib import Path

def run(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=90)

def inspect(path):
    p=Path(path)
    result={"file":str(p),"status":"BLOCKED","checks":{},"issues":[],"technical_score":0,
            "rights_approved":False,"user_approved":False,"publish_allowed":False}
    if not p.is_file() or p.stat().st_size==0:
        result["issues"].append("Missing or empty MP4")
        return result
    try:
        probe=run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)])
        if probe.returncode: raise ValueError(probe.stderr.strip())
        info=json.loads(probe.stdout)
        streams=info.get("streams",[])
        video=next((s for s in streams if s.get("codec_type")=="video"),None)
        audio=next((s for s in streams if s.get("codec_type")=="audio"),None)
        duration=float(info.get("format",{}).get("duration") or 0)
        w,h=(int(video.get("width",0)),int(video.get("height",0))) if video else (0,0)
        checks=result["checks"]
        checks["mp4_container"]=p.suffix.lower()==".mp4"
        checks["portrait_9_16"]=bool(w and h and abs(w/h-9/16)<0.012)
        checks["resolution_1080x1920"]=w>=1080 and h>=1920
        checks["duration_15_20s"]=15<=duration<=20
        checks["audio_stream_present"]=audio is not None
        checks["video_stream_present"]=video is not None
        checks["dimensions"]=[w,h]
        checks["duration_seconds"]=round(duration,2)
        # Decode the entire file, not just metadata: corrupt/truncated streams must fail closed.
        if video and duration>0:
            decode=run(["ffmpeg","-v","error","-xerror","-err_detect","explode",
                        "-i",str(p),"-map","0:v:0","-f","null","-"])
            checks["video_decodes_cleanly"]=decode.returncode==0
        else:
            checks["video_decodes_cleanly"]=False
        if audio and duration>0:
            decode_audio=run(["ffmpeg","-v","error","-xerror","-err_detect","explode",
                              "-i",str(p),"-map","0:a:0","-f","null","-"])
            checks["audio_decodes_cleanly"]=decode_audio.returncode==0
        else:
            checks["audio_decodes_cleanly"]=False
        if video and duration>0:
            black=run(["ffmpeg","-hide_banner","-nostats","-i",str(p),"-vf","blackdetect=d=0.5:pix_th=0.10","-an","-f","null","-"])
            checks["no_black_segments"]=black.returncode==0 and "black_start:" not in black.stderr
        else: checks["no_black_segments"]=False
        if audio and duration>0:
            silence=run(["ffmpeg","-hide_banner","-nostats","-i",str(p),"-af","silencedetect=noise=-45dB:d=2","-vn","-f","null","-"])
            checks["no_long_silence"]=silence.returncode==0 and "silence_start:" not in silence.stderr
        else: checks["no_long_silence"]=False
        weights={"mp4_container":10,"portrait_9_16":20,"resolution_1080x1920":10,"duration_15_20s":15,
                 "audio_stream_present":10,"video_stream_present":10,"no_black_segments":10,"no_long_silence":5,\n                 "video_decodes_cleanly":5,"audio_decodes_cleanly":5}
        result["technical_score"]=sum(weight for key,weight in weights.items() if checks.get(key) is True)
        result["issues"]=[key for key in weights if checks.get(key) is not True]
        result["issues"] += [key for key in ("video_decodes_cleanly","audio_decodes_cleanly") if checks.get(key) is not True]
        # Technical checks are not a visual-artifact review, rights clearance or user approval.
        result["status"]="TECHNICAL_PASS" if not result["issues"] else "BLOCKED"
    except (OSError,ValueError,subprocess.TimeoutExpired,json.JSONDecodeError) as exc:
        result["issues"].append(str(exc))
    return result

if __name__=="__main__":
    if len(sys.argv)!=2:
        print("Usage: python3 scripts/video_preflight.py FILE.mp4",file=sys.stderr)
        sys.exit(2)
    report=inspect(sys.argv[1])
    print(json.dumps(report,ensure_ascii=False,indent=2))
    sys.exit(0 if report["status"]=="TECHNICAL_PASS" else 1)
