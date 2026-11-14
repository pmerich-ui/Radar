"""Technical MP4 QA. Audio presence is not evidence of audible sound."""
import json
import re
import subprocess
from pathlib import Path

def _audible_audio(path):
    """Reject silent tracks; a pass is not a subjective listening test."""
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path),
         "-map", "0:a:0", "-vn", "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != 0:
        return False
    match = re.search(r"max_volume:\s*(-?inf|-?\d+(?:\.\d+)?)\s*dB", result.stderr)
    return bool(match and match.group(1) != "-inf" and float(match.group(1)) > -90)

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
        audio_present = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
        num, den = (int(x) for x in stream["r_frame_rate"].split("/"))
        duration = float(info["format"]["duration"])
        video_valid = (stream.get("codec_name") == "h264"
                       and stream.get("pix_fmt") == "yuv420p"
                       and (stream.get("width"), stream.get("height")) == (1080, 1920)
                       and den > 0 and 23 <= num / den <= 60
                       and 15 <= duration <= 30)
        if not video_valid or not audio_present:
            return {"status": "BLOCKED", "reason": "VIDEO_SPEC_MISMATCH",
                    "duration_seconds": duration, "publishable": False}
        if not _audible_audio(file):
            return {"status": "BLOCKED", "reason": "AUDIO_SILENT_OR_UNVERIFIED",
                    "duration_seconds": duration, "publishable": False}
        return {"status": "TECHNICAL_PASS", "reason": "VIDEO_TECHNICAL_CHECK",
                "duration_seconds": duration, "publishable": False,
                "requires": ["visual_review", "listening_review", "rights", "facts", "owner_approval"]}
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError, ZeroDivisionError, OverflowError):
        return {"status": "BLOCKED", "reason": "VIDEO_PROBE_FAILED", "publishable": False}

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("video")
    print(json.dumps(inspect(p.parse_args().video)))
