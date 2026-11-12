#!/usr/bin/env python3
"""Regression checks for DealRadar's fail-closed video preflight."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "scripts" / "video_preflight.py"

def check(path, expected_exit):
    p = subprocess.run([sys.executable, str(PREFLIGHT), str(path)], text=True, capture_output=True, timeout=150)
    assert p.returncode == expected_exit, (p.returncode, p.stdout, p.stderr)
    report = json.loads(p.stdout)
    assert report["publish_allowed"] is False
    assert report["rights_approved"] is False
    assert report["user_approved"] is False
    return report

with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)
    missing = check(folder / "missing.mp4", 1)
    assert missing["status"] == "BLOCKED"
    empty = folder / "empty.mp4"
    empty.touch()
    assert check(empty, 1)["status"] == "BLOCKED"
    invalid = folder / "invalid.mp4"
    invalid.write_bytes(b"not a video")
    assert check(invalid, 1)["status"] == "BLOCKED"
    fixture = folder / "fixture.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=24",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
                    "-t", "16", "-c:v", "libx264", "-preset", "ultrafast",
                    "-threads", "2", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(fixture)], check=True, timeout=180)
    report = check(fixture, 0)
    assert report["status"] == "TECHNICAL_PASS", report
    assert report["technical_score"] == 100, report
    assert report["checks"]["video_decodes_cleanly"] is True, report
    assert report["checks"]["audio_decodes_cleanly"] is True, report
    # A deliberately truncated real MP4 must never pass technical QA.
    truncated = folder / "truncated.mp4"
    with fixture.open("rb") as source, truncated.open("wb") as target:
        target.write(source.read(max(1024, fixture.stat().st_size // 2)))
    damaged = check(truncated, 1)
    assert damaged["status"] == "BLOCKED", damaged
    (ROOT / "qa-output").mkdir(exist_ok=True)
    (ROOT / "qa-output" / "preflight.json").write_text(json.dumps({"evidence_type": "SYNTHETIC_TEST_FIXTURE", "production_video": False, "publication_authorized": False, "preflight": report}, indent=2), encoding="utf-8")
    print("PASS: missing, empty, invalid and truncated MP4 blocked; synthetic fixture passes technical QA only; publishing remains blocked")
