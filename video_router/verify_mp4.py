"""Mechanical check for locally downloaded MP4. Not a substitute for human QA."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess

def inspect_mp4(file: str | Path, *, require_audio: bool = True) -> dict:
    p = Path(file)
    if not p.is_file() or p.suffix.lower() != ".mp4" or p.stat().st_size < 1024:
        raise ValueError("missing or empty MP4")
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(p)],
        capture_output=True, text=True, timeout=30, check=True)
    info = json.loads(proc.stdout)
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if v is None:
        raise ValueError("no video stream")
    width, height = int(v["width"]), int(v["height"])
    duration = float(info.get("format", {}).get("duration") or v.get("duration") or 0)
    if height <= width or abs(width / height - 9 / 16) > 0.025:
        raise ValueError("not vertical 9:16")
    if height < 480 or width < 270:
        raise ValueError("below 480p portrait equivalent")
    if not 15 <= duration <= 20.5:
        raise ValueError("final spot is not 15–20 seconds")
    if require_audio and a is None:
        raise ValueError("no audio stream")
    return {"width": width, "height": height, "duration_s": duration,
            "has_audio_stream": a is not None, "audio_audible": "NOT_CHECKED",
            "commercial_rights": "CHECK_SEPARATELY", "visual_qa": "PENDING",
            "ready_for_publication": False}
