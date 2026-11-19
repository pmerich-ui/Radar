"""DealRadar technical MP4 readiness audit. Never authorizes publication."""
from __future__ import annotations
import json
import math
import re
import subprocess
from pathlib import Path


def inspect_video(path: Path) -> dict:
    checks = {}
    try:
        raw = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_name,codec_type,width,height,r_frame_rate",
             "-of", "json", str(path)], text=True, timeout=30)
        data = json.loads(raw)
        streams = data["streams"]
        video = next(s for s in streams if s.get("codec_type") == "video")
        audio = next(s for s in streams if s.get("codec_type") == "audio")
        n, d = map(int, video["r_frame_rate"].split("/"))
        duration = float(data["format"]["duration"])
        checks = {
            "resolution_1080x1920": (video["width"], video["height"]) == (1080, 1920),
            "fps_30": d > 0 and abs(n / d - 30) < 0.01,
            "duration_15_to_20": math.isfinite(duration) and 15 <= duration <= 20,
            "video_h264": video.get("codec_name") == "h264",
            "audio_aac": audio.get("codec_name") == "aac",
            "nonempty_file": path.stat().st_size > 10000,
        }
        if not all(checks.values()):
            return {"file": str(path), "checks": checks, "technical_premium_pass": False}
        decode = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(path),
             "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
            capture_output=True, text=True, timeout=180)
        checks["full_audio_video_decode"] = decode.returncode == 0
        if not checks["full_audio_video_decode"]:
            return {"file": str(path), "checks": checks, "technical_premium_pass": False}
        volume = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path),
             "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=180)
        match = re.search(r"mean_volume:\s*(-?(?:\d+(?:\.\d+)?|inf))\s*dB", volume.stderr)
        level = float(match.group(1)) if match else float("-inf")
        checks["audio_detectably_non_silent"] = (
            volume.returncode == 0 and math.isfinite(level) and level >= -45)
        return {"file": str(path), "checks": checks,
                "mean_volume_db": level if math.isfinite(level) else None,
                "technical_premium_pass": all(checks.values()),
                "creative_qa": "NOT_VERIFIED", "rights": "RIGHTS_UNVERIFIED",
                "publishable": False}
    except (OSError, ValueError, KeyError, StopIteration,
            subprocess.SubprocessError, ZeroDivisionError) as exc:
        return {"file": str(path), "checks": checks, "technical_premium_pass": False,
                "error": type(exc).__name__, "publishable": False}


def audit(folder: Path = Path("output")) -> dict:
    videos = sorted(folder.glob("*.mp4")) if folder.exists() else []
    results = [inspect_video(p) for p in videos]
    report = {
        "videos_checked": len(results),
        "premium_technical_passed": sum(bool(r["technical_premium_pass"]) for r in results),
        "premium_ready": bool(results) and all(r["technical_premium_pass"] for r in results),
        "verified_real_deals": "NOT_VERIFIED",
        "licensed_assets": "RIGHTS_UNVERIFIED",
        "tiktok_publication": "DISABLED",
        "results": results,
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "readiness_audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False))
