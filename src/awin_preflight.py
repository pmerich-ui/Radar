"""Agent 05 credential presence check. Never exposes credential values."""
import json
import os
from pathlib import Path
from .awin_feed_fetch import validate_url

def check(value):
    if not value:
        return {"status": "BLOCKED", "reason": "AWIN_FEED_URL_NOT_CONFIGURED",
                "next_action": "Set repository Actions secret AWIN_FEED_URL."}
    try:
        validate_url(value)
    except ValueError:
        return {"status": "BLOCKED", "reason": "AWIN_FEED_URL_INVALID",
                "next_action": "Use an approved HTTPS productdata.awin.com feed URL."}
    return {"status": "READY", "reason": "AWIN_FEED_URL_CONFIGURED",
            "next_action": "Proceed to read-only Awin feed audit."}

def main():
    result = check(os.environ.get("AWIN_FEED_URL", ""))
    out = Path("reports/awin_preflight.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write("### DealRadar Agent 05 — Awin-Zugang\n\n")
            stream.write(f"**Status:** {result['status']}  \n")
            stream.write(f"**Code:** {result['reason']}  \n")
            stream.write(f"**Nächster Schritt:** {result['next_action']}\n")
    print(json.dumps(result))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write("ready=" + ("true" if result["status"] == "READY" else "false") + "\n")

if __name__ == "__main__":
    main()
