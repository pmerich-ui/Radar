"""Idempotent 24-hour TikTok snapshot eligibility; no network or publishing side effects."""
from datetime import timedelta
import fcntl
import json
import os
from pathlib import Path
import tempfile


def eligible(video_id, published_at, now, completed):
    """Return True only for a first 24h snapshot of a public video."""
    if not video_id or not published_at:
        return False
    if published_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("timezone-aware timestamps required")
    return now >= published_at + timedelta(hours=24) and video_id not in completed


def record_once(path, video_id, published_at, captured_at, metrics):
    """Persist a single snapshot atomically under an interprocess file lock (POSIX)."""
    # Metadata (publication time, URL, duration) is not a performance measurement.
    # A real zero is valid; null, empty strings and whitespace are not.
    performance_keys = {"TKPO07", "TKPO08", "TKPO09", "TKPO10", "TKPO11", "TKPO13", "TKPO15",
                        "views", "likes", "comments", "shares", "reach",
                        "fullVideoWatchedRate", "averageTimeWatched"}
    if not isinstance(metrics, dict) or not any(
        key in performance_keys and value is not None
        and (not isinstance(value, str) or bool(value.strip()))
        for key, value in metrics.items()
    ):
        return False  # No actual performance data: retry later.
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with (path.parent / (path.name + ".lock")).open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            return _record_locked(path, video_id, published_at, captured_at, metrics)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _record_locked(path, video_id, published_at, captured_at, metrics):
    snapshots = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not eligible(video_id, published_at, captured_at, snapshots):
        return False
    snapshots[video_id] = {
        "published_at": published_at.isoformat(),
        "captured_at": captured_at.isoformat(),
        "metrics": metrics,
    }
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".24h-", suffix=".tmp", delete=False) as handle:
            temp = Path(handle.name)
            json.dump(snapshots, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return True
