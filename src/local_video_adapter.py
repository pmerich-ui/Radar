"""Executable zero-credit local FFmpeg adapter for DealRadar.

Uses the existing original-illustration renderer. This is NOT an AI video provider
and is not evidence of creative quality, commercial rights, or publication approval.
"""
import argparse
import json
from pathlib import Path
from .producer import CATALOG, render
from .video_provider_router import registry, fallback
from .video_qa_agent import inspect

LOCAL = '[{"name":"local_ffmpeg","enabled":true,"commercial_rights":true,"supports_vertical":true,"credits":1,"cost_credits":0,"priority":1}]'

def run(output="output/router-demo.mp4"):
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    def attempt(provider):
        if provider.name != "local_ffmpeg":
            return {"status": "FAILED", "charged": False}
        render(CATALOG[0], target)
        qa = inspect(target)
        if qa["status"] != "TECHNICAL_PASS":
            return {"status": "FAILED", "charged": False}
        return {"status": "SUCCEEDED", "verified_file": str(target), "charged": False}
    outcome = fallback(registry(LOCAL), attempt)
    outcome["creative_qa"] = "NOT_VERIFIED"
    outcome["rights_review"] = "REQUIRED"
    outcome["quality_score"] = None
    outcome["publication_authorized"] = False
    return outcome

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="output/router-demo.mp4")
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=False))
