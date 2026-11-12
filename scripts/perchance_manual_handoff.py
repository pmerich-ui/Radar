#!/usr/bin/env python3
"""DealRadar: zero-cost Perchance image-preparation handoff.

Perchance.org terms prohibit automated/non-human access. This tool only creates
local prompts and a manifest for manual browser use. It never scrapes, calls
Perchance, generates a video, or publishes.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

STYLES = {
    "dance": {
        "title": "Drei Männer mit Damenfrisuren tanzen",
        "prompt": "Vertical 9:16, premium photorealistic Swiss comedy, three adult men wearing oversized playful women's wigs (blonde curls, black long curls, pink bouffant), coordinated funny dance poses in colorful modest stage outfits at a Swiss alpine lake, distinct consistent faces, full body visible, natural lighting, crisp realistic detail, clean composition, no words, no logos, no watermarks.",
        "motion": "Three adult performers dance in sync, exaggerated but natural steps, bouncy wigs, stable faces and hands, locked vertical framing, 10 seconds, funny unexpected finish, no text.",
    },
    "matterhorn_hair": {
        "title": "Matterhorn-Frisur im Schweizer Coiffeursalon",
        "prompt": "Vertical 9:16, photorealistic Swiss mockumentary smartphone footage aesthetic, adult male customer in an authentic Swiss hair salon, a professional stylist carefully shapes his real hair into a spectacular enormous Matterhorn mountain silhouette, visibly realistic hair strands and believable construction, serious reactions, natural Swiss daylight, authentic skin and hands, no cartoon, no CGI-looking characters, no words, no logos, no watermarks.",
        "motion": "A Swiss hairdresser carefully adjusts the adult customer’s giant Matterhorn-shaped hairstyle; the customer inspects the mirror and deadpans with a straight face, believable human motion and hair physics, handheld smartphone mockumentary aesthetic, 10 seconds, no text.",
    },
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="production/perchance_handoff")
    args = parser.parse_args()
    dest = Path(args.out)
    dest.mkdir(parents=True, exist_ok=True)
    manifest = {"source": "https://perchance.org/ai-text-to-image-generator",
                "workflow": "manual_browser_only", "cost_chf": 0,
                "status": "AWAITING_MANUAL_IMAGES",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "commercial_rights": "Perchance-generated outputs allowed by its terms; review third-party rights",
                "api_access": False, "automatic_scraping": False,
                "publication_allowed": False, "video_generated": False,
                "items": []}
    for key, spec in STYLES.items():
        (dest / f"{key}_image_prompt.txt").write_text(spec["prompt"]+"\n", encoding="utf-8")
        (dest / f"{key}_motion_prompt.txt").write_text(spec["motion"]+"\n", encoding="utf-8")
        manifest["items"].append({"id": key, "title": spec["title"],
            "image_prompt_file": f"{key}_image_prompt.txt",
            "motion_prompt_file": f"{key}_motion_prompt.txt",
            "image_status": "NOT_GENERATED", "video_status": "NOT_GENERATED",
            "qa_status": "NOT_CHECKED", "approval": False})
    (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Created manual Perchance handoff at {dest}; no generation or publication performed.")

if __name__ == "__main__":
    main()
