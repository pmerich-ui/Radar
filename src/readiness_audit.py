"""DealRadar production readiness audit. Fail closed on premium and publishing claims."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

def inspect_video(path: Path) -> dict:
    try:
        raw = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_name,codec_type,width,height,r_frame_rate",
             "-of", "json", str(path)], text=True, timeout=30
        )
        data = json.loads(raw)
        video = next(s for s in data["streams"] if s.get("codec_type") == "video")
        audio = any(s.get("codec_type") == "audio" and s.get("codec_name") == "aac" for s in data["streams"])
        n, d = map(int, video["r_frame_rate"].split("/"))
        duration = float(data["format"]["duration"])
        checks = {
            "resolution_1080x1920": (video["width"], video["height"]) == (1080, 1920),
            "fps_30": d != 0 and abs(n / d - 30) < 0.01,
            "duration_15_to_30": 15 <= duration <= 30,
            "video_h264": video.get("codec_name") == "h264",
            "audio_aac": audio,
            "nonempty_file": path.stat().st_size > 10000,
        }
        decode = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"], capture_output=True, text=True, timeout=180)
        checks["full_decode"] = decode.returncode == 0
        return {"file": str(path), "checks": checks, "technical_premium_pass": all(checks.values())}
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError, subprocess.TimeoutExpired) as exc:
        return {"file": str(path), "technical_premium_pass": False, "error": type(exc).__name__}

def audit(folder: Path = Path("output")) -> dict:
    videos = sorted(folder.glob("*.mp4")) if folder.exists() else []
    results = [inspect_video(p) for p in videos]
    report = {
        "videos_checked": len(results),
        "premium_technical_passed": sum(bool(r["technical_premium_pass"]) for r in results),
        "premium_ready": bool(results) and all(r["technical_premium_pass"] for r in results),
        "verified_real_deals": "NOT_VERIFIED",
        "licensed_assets": "NOT_VERIFIED",
        "tiktok_publication": "DISABLED",
        "results": results,
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "readiness_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report

if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False))
