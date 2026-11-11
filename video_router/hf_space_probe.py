"""Hugging Face public Gradio Space read-only API discovery.

This adapter intentionally does NOT submit jobs: individual Space/model license,
free account quota, model parameters, and 9:16 export must be verified first.
"""
from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen
import json

@dataclass(frozen=True)
class SpaceProbe:
    space_id: str
    status: str
    endpoints: tuple[str, ...]
    reason: str

def inspect_public_space(space_id: str, *, timeout: int = 12) -> SpaceProbe:
    if len(space_id.split("/")) != 2 or any(not p.replace("-", "").replace("_", "").replace(".", "").isalnum() for p in space_id.split("/")):
        raise ValueError("invalid Hugging Face Space ID")
    # Public Hub metadata is read-only and does not use paid inference.
    url = "https://huggingface.co/api/spaces/" + quote(space_id, safe="/")
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "DealRadar-ReadOnlySpaceAudit/1.0"})
    with urlopen(req, timeout=timeout) as response:
        info = json.load(response)
    if info.get("sdk") != "gradio":
        return SpaceProbe(space_id, "BLOCKED", (), "not a Gradio Space")
    if info.get("private") is True:
        return SpaceProbe(space_id, "BLOCKED", (), "private Space")
    runtime = info.get("runtime") or {}
    stage = runtime.get("stage") or "UNKNOWN"
    if stage != "RUNNING":
        return SpaceProbe(space_id, "BLOCKED", (), "runtime not running: " + str(stage))
    return SpaceProbe(space_id, "DISCOVERABLE", (), "public Gradio API available; inspect Use via API before integration")

def require_hf_generation_approval(*, commercial_license_verified: bool,
    quota_verified: bool, model_supports_9_16: bool,
    free_account_confirmed: bool, approved_space_owner_terms: bool) -> bool:
    return all((commercial_license_verified, quota_verified,
                model_supports_9_16, free_account_confirmed,
                approved_space_owner_terms))
