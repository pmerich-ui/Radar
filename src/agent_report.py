"""Read-only, deterministic operating status for DealRadar agent queue."""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def report(root=ROOT):
    registry = json.loads((root / "agents" / "registry.json").read_text(encoding="utf-8"))
    roles = registry["roles"]
    installed = sum((root / "agents" / (role["id"] + "-" + role["slug"] + ".md")).is_file() for role in roles)
    implemented = [r for r in roles if r.get("executor")]
    receipts = []
    for path in sorted((root / "queue" / "results").glob("*.json")):
        try:
            receipts.append(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            receipts.append({"status": "MALFORMED_RESULT", "task_id": path.stem})
    statuses = Counter(str(r.get("status", "UNKNOWN")) for r in receipts)
    pending = len(list((root / "queue" / "pending").glob("*.json")))
    lines = [
        "# DealRadar AG – technischer Status",
        "",
        "Automatisch erzeugter, quellengestützter Bericht. Keine Aussage über ausgeführte TikTok-Veröffentlichungen.",
        "",
        f"- Agentendefinitionen: **{installed}/{len(roles)}**",
        f"- Lokal implementierte, lesende Agenten: **{len(implemented)}** ({', '.join(r['id'] for r in implemented)})",
        "- Aktive KI-Modell-Agenten: **0** (LLM_NOT_CONFIGURED)",
        "- Veröffentlichung: **GESPERRT** (DRY_RUN, keine bestätigte Freigabe)",
        f"- Aufgaben ausstehend: **{pending}**",
        f"- Aufgaben mit Ergebnisdatei: **{len(receipts)}**",
        "",
        "## Ergebnisstatus",
        ""
    ]
    lines.extend(f"- {k}: {v}" for k, v in sorted(statuses.items()))
    lines.extend(["", "## Grenzen", "",
        "COMPLETED bei Agent 02/37 belegt nur lokale, lesende Strukturprüfungen.",
        "GitHub-Actions-Ausführung und externe APIs sind damit nicht automatisch end-to-end bestätigt.",
        "Unbekannte Einnahmen sind DATA_UNAVAILABLE und keine bestätigten CHF 0.",
        ""])
    return "\n".join(lines)

def main():
    out = ROOT / "reports" / "status.md"
    out.parent.mkdir(exist_ok=True)
    value = report()
    if not out.exists() or out.read_text(encoding="utf-8") != value:
        out.write_text(value, encoding="utf-8")
    print(value)

if __name__ == "__main__":
    main()
