"""Agent 21 technical video QA; no claim of creative or rights approval."""
import json
import re
import subprocess
from pathlib import Path

def inspect(path):
    file = Path(path)
    if not file.is_file() or file.suffix.lower() != ".mp4":
        return {"status": "BLOCKED", "reason": "MP4_MISSING", "publishable": False}
    try:
        raw = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_name,codec_type,width,height,r_frame_rate,pix_fmt",
             "-of", "json", str(file)], text=True, timeout=30)
        info = json.loads(raw)
        stream = next(s for s in info.get("streams", []) if s.get("codec_type") == "video")
        num, den = (int(x) for x in stream["r_frame_rate"].split("/"))
        duration = float(info["format"]["duration"])
        audio = next((a for a in info.get("streams", []) if a.get("codec_type") == "audio"), None)
        valid = (audio is not None and audio.get("codec_name") == "aac"
                 and stream.get("codec_name") == "h264"
                 and stream.get("pix_fmt") == "yuv420p"
                 and (stream.get("width"), stream.get("height")) == (1080, 1920)
                 and den > 0 and 23 <= num / den <= 60
                 and 15 <= duration <= 20)
        if valid:
            decoded = subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(file),
                 "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
                capture_output=True, text=True, timeout=120)
            if decoded.returncode:
                return {"status": "BLOCKED", "reason": "DECODE_FAILED", "publishable": False}
            volume = subprocess.run(
                ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(file),
                 "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"],
                capture_output=True, text=True, timeout=120)
            match = re.search(r"mean_volume:\s*(-?(?:\d+(?:\.\d+)?|inf))\s*dB", volume.stderr)
            if volume.returncode or not match or float(match.group(1)) < -45:
                return {"status": "BLOCKED", "reason": "AUDIO_SILENT_OR_TOO_QUIET",
                        "publishable": False}
        return {"status": "TECHNICAL_PASS" if valid else "BLOCKED",
                "reason": "VIDEO_TECHNICAL_CHECK" if valid else "VIDEO_SPEC_MISMATCH",
                "duration_seconds": duration, "publishable": False,
                "requires": ["visual_review", "rights", "facts", "owner_approval"]}
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError, subprocess.TimeoutExpired, ZeroDivisionError):
        return {"status": "BLOCKED", "reason": "VIDEO_PROBE_FAILED", "publishable": False}

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("video")
    args = p.parse_args()
    print(json.dumps(inspect(args.video)))
