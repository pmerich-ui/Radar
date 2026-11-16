"""Regression checks for 24h snapshot performance-data eligibility."""
from datetime import datetime, timedelta, timezone
import json
from src.v5_analytics import record_once

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)
PUBLISHED = NOW - timedelta(hours=25)

def test_metadata_only_does_not_finalize(tmp_path):
    p = tmp_path / "snapshots.json"
    assert not record_once(p, "video1", PUBLISHED, NOW, {"TKPO02": "20261115", "TKPO03": "https://example.com", "TKPO06": "18"})
    assert not p.exists()

def test_missing_performance_does_not_finalize(tmp_path):
    p = tmp_path / "snapshots.json"
    assert not record_once(p, "video1", PUBLISHED, NOW, {"TKPO07": None, "TKPO08": "  "})
    assert not p.exists()

def test_zero_views_is_valid(tmp_path):
    p = tmp_path / "snapshots.json"
    assert record_once(p, "video1", PUBLISHED, NOW, {"TKPO07": 0, "TKPO03": "https://example.com"})
    assert p.exists()
