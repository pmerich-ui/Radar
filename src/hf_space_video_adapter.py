"""Fail-closed adapter for explicitly approved Hugging Face Gradio Spaces.

No network call unless enabled. A completed Gradio event is NOT proof of
commercial rights, video quality, file integrity, or publishing permission.
No credentials or generated content are logged.
"""
import json
import os
import re
import urllib.request
from urllib.parse import urlsplit

class CloudRenderError(RuntimeError):
    pass

def validate_space_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.username or parsed.password or
            parsed.port is not None or parsed.query or parsed.fragment or
            not re.fullmatch(r"[a-z0-9][a-z0-9-]*\\.hf\\.space", parsed.hostname or "") or
            parsed.path not in ("", "/")):
        raise CloudRenderError("Only a direct HTTPS *.hf.space Gradio host is accepted")
    return "https://" + parsed.hostname

def validate_api_name(api_name):
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{0,63}", api_name):
        raise CloudRenderError("Invalid Gradio API name")
    return api_name

def submit(space_url, api_name, data, *, enabled=False, token=None):
    if not enabled:
        return {"status": "DISABLED", "publication_authorized": False}
    host = validate_space_url(space_url)
    name = validate_api_name(api_name)
    if not isinstance(data, list):
        raise CloudRenderError("Gradio input must be a list")
    payload = json.dumps({"data": data}).encode("utf-8")
    if len(payload) > 100_000:
        raise CloudRenderError("Request exceeds maximum size")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(host + "/gradio_api/call/" + name,
                                     data=payload, headers=headers, method="POST")
    # No redirect following: prevent credentials/payload being sent elsewhere.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise CloudRenderError("Redirect refused")
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=30) as response:
        result = json.loads(response.read(100_000))
    event_id = result.get("event_id") if isinstance(result, dict) else None
    if not isinstance(event_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", event_id):
        raise CloudRenderError("No validated Gradio event ID")
    return {"status": "SUBMITTED_UNVERIFIED", "event_id": event_id,
            "publication_authorized": False, "rendered_file": None,
            "rights_review": "REQUIRED", "creative_review": "REQUIRED",
            "owner_approval": False}

if __name__ == "__main__":
    if os.getenv("HF_SPACE_ENABLED") != "1":
        print(json.dumps({"status": "DISABLED", "publication_authorized": False}))
    else:
        space = os.environ["HF_SPACE_URL"]
        api = os.environ["HF_SPACE_API_NAME"]
        inputs = json.loads(os.environ["HF_SPACE_INPUTS_JSON"])
        print(json.dumps(submit(space, api, inputs, enabled=True,
                                token=os.getenv("HF_TOKEN"))))
