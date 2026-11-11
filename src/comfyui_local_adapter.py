"""Opt-in local ComfyUI adapter. Never sends prompts to remote hosts.

Requires a user-provided, reviewed ComfyUI API workflow JSON. This module
does not install models, claim commercial rights, or authorize publication.
"""
import json
import os
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

class LocalRenderError(RuntimeError):
    pass

def _local_url(url):
    p = urlsplit(url)
    if p.scheme != "http" or p.hostname not in ("127.0.0.1", "localhost") or p.username or p.password or p.query or p.fragment or p.port != 8188:
        raise LocalRenderError("Only local ComfyUI http://127.0.0.1:8188 is allowed")
    return "http://127.0.0.1:8188"

def submit_workflow(workflow_file, *, endpoint="http://127.0.0.1:8188", enabled=False):
    """Submit one pre-reviewed workflow; returns prompt ID, NOT a rendered file."""
    if not enabled:
        return {"status": "DISABLED", "publication_authorized": False}
    base = _local_url(endpoint)
    path = Path(workflow_file)
    if not path.is_file() or path.stat().st_size > 2_000_000:
        raise LocalRenderError("Workflow missing or oversized")
    workflow = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(workflow, dict) or not workflow:
        raise LocalRenderError("Expected nonempty ComfyUI API workflow object")
    # Prevent silently substituting arbitrary server endpoints.
    payload = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(base + "/prompt", data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.loads(response.read(100_000))
    if not isinstance(data, dict) or not isinstance(data.get("prompt_id"), str):
        raise LocalRenderError("ComfyUI did not confirm prompt submission")
    return {"status": "SUBMITTED_UNVERIFIED", "prompt_id": data["prompt_id"],
            "publication_authorized": False, "rendered_file": None,
            "creative_review": "REQUIRED", "rights_review": "REQUIRED",
            "owner_approval": False}

if __name__ == "__main__":
    workflow_file = os.environ.get("COMFYUI_WORKFLOW_JSON", "")
    if not workflow_file:
        raise SystemExit("Set COMFYUI_WORKFLOW_JSON to a reviewed local workflow")
    print(json.dumps(submit_workflow(workflow_file,
        enabled=os.environ.get("COMFYUI_LOCAL_ENABLED") == "1")))
