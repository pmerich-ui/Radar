"""Technical MP4 gate. This is not creative, legal or publication approval."""
import json
import math
import re
import subprocess
from pathlib import Path

def silence_fraction(log, duration):
    """Fraction of timeline detected as silence, including trailing silence."""
    if not math.isfinite(duration) or duration <= 0:
        return 1.0
    events = re.findall(r"silence_(start|end):\\s*([0-9]+(?:\\.[0-9]+)?)", log)
    start = None
    silent = 0.0
    for kind, value in events:
        t = max(0.0, min(duration, float(value)))
        if kind == "start":
            if start is None:
                start = t
        elif start is not None:
            silent += max(0.0, t - start)
            start = None
    if start is not None:
        silent += max(0.0, duration - start)
    return min(1.0, silent / duration)


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
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
        num, den = (int(x) for x in video["r_frame_rate"].split("/"))
        duration = float(info["format"]["duration"])
        valid = (video.get("codec_name") == "h264"
                 and video.get("pix_fmt") == "yuv420p"
                 and (video.get("width"), video.get("height")) == (1080, 1920)
                 and den > 0 and 23 <= num / den <= 60
                 and math.isfinite(duration) and 15 <= duration <= 20
                 and audio is not None and audio.get("codec_name") == "aac")
        if not valid:
            return {"status": "BLOCKED", "reason": "VIDEO_SPEC_MISMATCH",
                    "duration_seconds": duration, "publishable": False}
        # Decode the complete video and audio streams, not merely their headers.
        decoded = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(file),
             "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
            capture_output=True, text=True, timeout=180)
        if decoded.returncode:
            return {"status": "BLOCKED", "reason": "MEDIA_DECODE_FAILED",
                    "duration_seconds": duration, "publishable": False}
        # An audio stream can exist but be completely silent. Fail closed.
        volume = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "info", "-i", str(file),
             "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=180)
        if volume.returncode:
            return {"status": "BLOCKED", "reason": "AUDIO_ANALYSIS_FAILED",
                    "publishable": False}
        matches = re.findall(r"max_volume:\s*(-?(?:\d+(?:\.\d+)?|inf)) dB", volume.stderr)
        peak = float(matches[-1]) if matches else float("-inf")
        if not math.isfinite(peak) or peak < -45:
            return {"status": "BLOCKED", "reason": "AUDIO_SILENT_OR_TOO_QUIET",
                    "audio_peak_dbfs": peak, "publishable": False}
        mean_matches = re.findall(r"mean_volume:\\s*(-?(?:\\d+(?:\\.\\d+)?|inf)) dB", volume.stderr)
        mean = float(mean_matches[-1]) if mean_matches else float("-inf")
        if not math.isfinite(mean) or mean < -35 or peak > -0.1:
            return {"status": "BLOCKED", "reason": "AUDIO_LEVEL_UNSAFE",
                    "audio_peak_dbfs": peak, "audio_mean_dbfs": mean, "publishable": False}
        silence = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "info", "-i", str(file),
             "-map", "0:a:0", "-af", "silencedetect=noise=-40dB:d=0.25",
             "-f", "null", "-"], capture_output=True, text=True, timeout=180)
        if silence.returncode:
            return {"status": "BLOCKED", "reason": "AUDIO_SILENCE_ANALYSIS_FAILED",
                    "publishable": False}
        fraction = silence_fraction(silence.stderr, duration)
        if fraction > 0.35:
            return {"status": "BLOCKED", "reason": "AUDIO_EXCESSIVE_SILENCE",
                    "silence_fraction": fraction, "publishable": False}
        return {"status": "TECHNICAL_PASS", "reason": "MEDIA_TECHNICAL_CHECK",
                "duration_seconds": duration, "audio_peak_dbfs": peak,
                "publishable": False,
                "requires": ["visual_review", "creative_qa_85", "rights", "facts", "owner_approval"]}
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError,
            subprocess.TimeoutExpired, ZeroDivisionError):
        return {"status": "BLOCKED", "reason": "VIDEO_PROBE_FAILED", "publishable": False}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    args = parser.parse_args()
    print(json.dumps(inspect(args.video)))
