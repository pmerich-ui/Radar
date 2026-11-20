"""Strict, fail-closed media preflight. Does not certify creativity or licensing."""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

def _run(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)

def inspect(path: str | Path) -> dict:
    p = Path(path)
    checks = {}
    evidence = {}
    try:
        if not p.is_file():
            return {"passed": False, "checks": {"file_exists": False}, "evidence": {}}
        checks["nonempty_file"] = p.stat().st_size > 10000
        probe = _run(["ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
            "-of", "json", str(p)], 30)
        if probe.returncode != 0:
            return {"passed": False, "checks": {**checks, "ffprobe": False}, "evidence": {"error": probe.stderr[-500:]}}
        info = json.loads(probe.stdout)
        streams = info.get("streams", [])
        video = [s for s in streams if s.get("codec_type") == "video"]
        audio = [s for s in streams if s.get("codec_type") == "audio"]
        duration = float(info.get("format", {}).get("duration", 0))
        checks["duration_15_to_20"] = 15 <= duration <= 20
        checks["resolution_1080x1920"] = len(video) == 1 and (video[0].get("width"), video[0].get("height")) == (1080, 1920)
        checks["video_h264"] = len(video) == 1 and video[0].get("codec_name") == "h264"
        checks["audio_aac"] = bool(audio) and audio[0].get("codec_name") == "aac"
        evidence["duration_seconds"] = duration
        decoded = _run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(p),
            "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"])
        checks["full_av_decode"] = decoded.returncode == 0
        evidence["decode_error"] = decoded.stderr[-500:] if decoded.returncode else ""
        if audio:
            volume = _run(["ffmpeg", "-nostdin", "-v", "info", "-i", str(p),
                "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"])
            match = re.search(r"mean_volume:\s*(-?(?:\d+(?:\.\d+)?|inf)) dB", volume.stderr)
            level = float(match.group(1)) if match else float("-inf")
            evidence["mean_volume_db"] = level if level != float("-inf") else None
            checks["audio_not_silent"] = volume.returncode == 0 and level > -55
        else:
            checks["audio_not_silent"] = False
        evidence["creative_review"] = "REQUIRED"
        evidence["commercial_rights"] = "RIGHTS_UNVERIFIED"
        return {"passed": all(checks.values()), "checks": checks, "evidence": evidence,
                "publication_allowed": False}
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        return {"passed": False, "checks": checks, "evidence": {"error": type(exc).__name__},
                "publication_allowed": False}

if __name__ == "__main__":
    import sys
    print(json.dumps(inspect(sys.argv[1]), ensure_ascii=False, indent=2))
