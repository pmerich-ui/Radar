"""Agent 21 technical video QA; no claim of creative or rights approval."""
import json
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
        audio = next(s for s in info.get("streams", []) if s.get("codec_type") == "audio")
        num, den = (int(x) for x in stream["r_frame_rate"].split("/"))
        duration = float(info["format"]["duration"])
        valid = (stream.get("codec_name") == "h264"
                 and stream.get("pix_fmt") == "yuv420p"
                 and (stream.get("width"), stream.get("height")) == (1080, 1920)
                 and audio.get("codec_name") in {"aac", "mp3"}
                 and den > 0 and 23 <= num / den <= 60
                 and 15 <= duration <= 20)
        if valid:
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(file),
                            "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
                           check=True, capture_output=True, timeout=120)
            volume = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-i", str(file),
                                     "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"],
                                    check=True, capture_output=True, text=True, timeout=120)
            import re
            match = re.search(r"max_volume:\\s*(-?(?:\\d+(?:\\.\\d+)?|inf)) dB", volume.stderr)
            if not match or match.group(1) == "-inf" or float(match.group(1)) < -50:
                return {"status": "BLOCKED", "reason": "AUDIO_SILENT_OR_UNVERIFIED", "publishable": False}
        return {"status": "TECHNICAL_PASS" if valid else "BLOCKED",
                "reason": "VIDEO_TECHNICAL_CHECK" if valid else "VIDEO_SPEC_MISMATCH",
                "duration_seconds": duration, "publishable": False,
                "requires": ["audible_speech_review", "visual_review", "rights", "facts", "owner_approval"]}
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError, ZeroDivisionError):
        return {"status": "BLOCKED", "reason": "VIDEO_PROBE_FAILED", "publishable": False}

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("video")
    args = p.parse_args()
    print(json.dumps(inspect(args.video)))
