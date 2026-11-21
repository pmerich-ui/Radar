"""Zero-cost local FFmpeg illustration renderer for development only.

A technical render is not proof of photorealism, commercial rights, or approval.
This adapter does not publish, and never claims licensed generation credits.
"""
import argparse
import json
from pathlib import Path
from .producer import CATALOG, render
from .video_qa_agent import inspect
from .video_provider_router import plan

# This renderer is deliberately INELIGIBLE for rights-gated production routing.
# Local execution below is for technical diagnostics, not publication.
LOCAL = '[{"name":"local_ffmpeg","enabled":true,"commercial_rights":false,"supports_vertical":true,"credits":0,"cost_credits":0,"priority":1}]'

def run(output="output/router-demo.mp4"):
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "BLOCKED",
        "provider": "local_ffmpeg",
        "creative_qa": "NOT_VERIFIED",
        "rights_review": "RIGHTS_UNVERIFIED",
        "quality_score": None,
        "publication_authorized": False,
        "production_routing": plan(LOCAL),
    }
    try:
        render(CATALOG[0], target)
        qa = inspect(target)
        result["technical_qa"] = qa
        if qa.get("status") == "TECHNICAL_PASS":
            result.update(status="RENDERED_UNREVIEWED", file=str(target))
        else:
            result["status"] = "TECHNICAL_QA_FAILED"
    except Exception as exc:
        result["status"] = "RENDER_FAILED"
        result["error_type"] = type(exc).__name__
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="output/router-demo.mp4")
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=False))
