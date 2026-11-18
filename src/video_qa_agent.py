"""Technical MP4 inspection. A pass never implies creative, rights or publication approval."""
import json
import math
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
        streams = info.get("streams", [])
        video = next(s for s in streams if s.get("codec_type") == "video")
        audio = next(s for s in streams if s.get("codec_type") == "audio")
        num, den = (int(x) for x in video["r_frame_rate"].split("/"))
        duration = float(info["format"]["duration"])
        valid = (video.get("codec_name") == "h264"
                 and video.get("pix_fmt") == "yuv420p"
                 and (video.get("width"), video.get("height")) == (1080, 1920)
                 and den > 0 and 23 <= num / den <= 60
                 and math.isfinite(duration) and 15 <= duration <= 20
                 and bool(audio.get("codec_name")))
        if not valid:
            return {"status": "BLOCKED", "reason": "VIDEO_SPEC_MISMATCH",
                    "duration_seconds": duration, "publishable": False}
        # Decode the complete file, including audio. A valid container alone is insufficient.
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-xerror",
                        "-i", str(file), "-map", "0:v:0", "-map", "0:a:0",
                        "-f", "null", "-"], check=True, timeout=180,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        # volumedetect uses decoded PCM samples; a silent audio stream is not acceptable.
        loudness = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(file),
             "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"],
            check=True, timeout=180, capture_output=True, text=True)
        import re
        match = re.search(r"mean_volume:\\s*(-?(?:\\d+(?:\\.\\d+)?|inf))\\s*dB", loudness.stderr)
        if not match or not math.isfinite(float(match.group(1))) or float(match.group(1)) < -45:
            return {"status": "BLOCKED", "reason": "AUDIO_SILENT_OR_TOO_QUIET",
                    "publishable": False}
        return {"status": "TECHNICAL_PASS", "reason": "VIDEO_AUDIO_DECODE_AND_LEVEL_CHECK",
                "duration_seconds": duration, "mean_volume_db": float(match.group(1)),
                "publishable": False,
                "requires": ["visual_review", "creative_qa_85", "rights", "facts", "owner_approval"]}
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError, ZeroDivisionError):
        return {"status": "BLOCKED", "reason": "VIDEO_PROBE_OR_DECODE_FAILED",
                "publishable": False}

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("video")
    args = p.parse_args()
    print(json.dumps(inspect(args.video)))
