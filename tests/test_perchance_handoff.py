#!/usr/bin/env python3
"""Regression: Perchance handoff never claims generated media or publication rights."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "handoff"
    result = subprocess.run([sys.executable, str(ROOT / "scripts/perchance_manual_handoff.py"),
                             "--out", str(out)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    data = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert data["workflow"] == "manual_browser_only"
    assert data["api_access"] is False
    assert data["automatic_scraping"] is False
    assert data["publication_allowed"] is False
    assert data["video_generated"] is False
    assert {item["id"] for item in data["items"]} == {"dance", "matterhorn_hair"}
    assert data["commercial_rights"].startswith("UNVERIFIED")
    assert data["cost_chf"] == 0  # local prompt export only; not provider pricing
    creative = json.loads((ROOT / "production/creative/coiffeur_matterhorn_2026-11-12.json").read_text(encoding="utf-8"))
    assert creative["status"] == "DRAFT_NOT_RENDERED"
    assert creative["rights"]["commercial_license"] == "UNVERIFIED"
    assert all(value is False for key, value in creative["gates"].items() if isinstance(value, bool))
    matterhorn = next(item for item in data["items"] if item["id"] == "matterhorn_hair")
    image_prompt = (out / matterhorn["image_prompt_file"]).read_text(encoding="utf-8").lower()
    motion_prompt = (out / matterhorn["motion_prompt_file"]).read_text(encoding="utf-8").lower()
    assert "adult woman" in image_prompt and "woman" in motion_prompt
    assert "matterhorn" in image_prompt and "matterhorn" in motion_prompt
    for item in data["items"]:
        assert item["image_status"] == "NOT_GENERATED"
        assert item["video_status"] == "NOT_GENERATED"
        assert item["approval"] is False
        for field in ("image_prompt_file", "motion_prompt_file"):
            p = out / item[field]
            assert p.is_file() and p.read_text(encoding="utf-8").strip()
print("PASS: manual handoff is fail-closed and produces two prompt sets (dance and Matterhorn hair)")
