"""Buffer API integration: discovery and explicitly gated scheduling.

Never run a write without --publish, BUFFER_API_KEY and a valid public MP4 URL.
The CLI defaults to read-only discovery. No token is printed.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys, urllib.request
from zoneinfo import ZoneInfo

API = "https://api.buffer.com"
CHANNELS_QUERY = """query DealRadarChannels { account { organizations { id channels { id name service } } } }"""
MUTATION = """mutation DealRadarSchedule($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id dueAt status } } ... on MutationError { message } } }"""

def call(query: str, variables: dict | None = None) -> dict:
    key = os.environ.get("BUFFER_API_KEY")
    if not key:
        raise RuntimeError("BUFFER_API_KEY missing: add it as a GitHub Actions secret; never paste it into chat")
    data = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=data, headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
    }, method="POST")
    with urllib.request.urlopen(req, timeout=25) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError("Buffer GraphQL returned errors: " + str([x.get("message") for x in result["errors"]]))
    return result.get("data", {})

def to_utc(date: str, clock: str) -> str:
    local = dt.datetime.fromisoformat(date + "T" + clock).replace(tzinfo=ZoneInfo("Europe/Zurich"))
    if local.astimezone(ZoneInfo("Europe/Zurich")).strftime("%Y-%m-%dT%H:%M") != date + "T" + clock:
        raise ValueError("Nonexistent Switzerland local time")
    if local <= dt.datetime.now(ZoneInfo("Europe/Zurich")):
        raise ValueError("Scheduling time must be in the future")
    return local.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def validate_url(url: str) -> None:
    if not url.startswith("https://") or not url.lower().split("?")[0].endswith(".mp4"):
        raise ValueError("A direct HTTPS .mp4 URL is required")
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise ValueError("Video not publicly reachable")
        if "video/" not in response.headers.get("Content-Type", ""):
            raise ValueError("Public URL does not serve video content")

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--discover", action="store_true", help="Read connected channels; no changes")
    p.add_argument("--publish", action="store_true", help="Explicitly authorize one scheduled post")
    p.add_argument("--channel-id")
    p.add_argument("--date", help="YYYY-MM-DD, Switzerland local")
    p.add_argument("--time", help="HH:MM, Switzerland local")
    p.add_argument("--video-url")
    p.add_argument("--caption")
    a = p.parse_args()
    if a.discover or not a.publish:
        print(json.dumps(call(CHANNELS_QUERY), ensure_ascii=False, indent=2))
        return
    if not all((a.channel_id, a.date, a.time, a.video_url, a.caption)):
        p.error("Publishing requires --channel-id --date --time --video-url --caption")
    due = to_utc(a.date, a.time)
    validate_url(a.video_url)
    payload = {"input": {"text": a.caption, "channelId": a.channel_id,
        "schedulingType": "automatic", "mode": "customScheduled", "dueAt": due,
        "assets": [{"video": {"url": a.video_url}}]}}
    result = call(MUTATION, payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    post = result.get("createPost", {})
    if not post.get("post", {}).get("id"):
        raise RuntimeError("Buffer did not confirm a scheduled post ID")

if __name__ == "__main__":
    main()
