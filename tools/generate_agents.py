"""Generate and validate DealRadar agent contracts from agents/registry.json.

No network, credentials, AI models or publishing. Use --check in CI. --write
creates/replaces contracts with deterministic content from the registry.
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"agents"/"registry.json"

def load():
    doc=json.loads(REGISTRY.read_text(encoding="utf-8"))
    roles=doc.get("roles",[])
    expected=[f"{i:02d}" for i in range(1,39)]
    if [r.get("id") for r in roles] != expected:
        raise ValueError("Registry must contain exactly 38 unique ordered roles 01-38")
    if len(set(r.get("slug") for r in roles))!=38:
        raise ValueError("Registry slugs must be unique")
    for r in roles:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",r["slug"]):
            raise ValueError("Invalid role slug "+repr(r["slug"]))
        if not r.get("name"):
            raise ValueError("Role name missing")
    return roles

def render(r):
    return f"""# Agent {r['id']}: {r['name']}

## Mission
Arbeite in der benannten DealRadar-Funktion nur mit nachweisbaren Quellen und explizit genehmigten Aufgaben.

## Eingaben
task_id, freigegebene Quellen und GitHub-Artefakte. Fehlende Werte: DATA_UNAVAILABLE.

## Ausgaben
agent_id, task_id, timestamp_utc, evidence_level, source, status, blockers und next_action.

## Werkzeuge
Lokale Python-Skripte, GitHub Actions und nur erlaubte lesende APIs.

## Autonomiestufe
{r['autonomy']}; externe Schreibzugriffe, Geheimnisse, Ausgaben und Live-Veröffentlichungen erfordern gesonderte Eigentümerfreigabe.

## Qualitätskriterien/Kennzahlen
Evidenz statt Behauptung; wiederholbare Ergebnisse; kein Doppelauftrag; keine zusätzlichen Ausgaben.

## Eskalation
Agent 01 für Blockaden, Agent 04 für Eigentümerfreigabe, Agenten 21–23 für QA und Compliance.

## Verbote
Keine erfundenen Fakten, Einnahmen oder erreichten Veröffentlichungen. Keine Secrets in Logs.

## Laufzeitstatus
Executor: {r['executor'] or 'NOT_IMPLEMENTED_OR_LLM_NOT_CONFIGURED'}. Ein vorhandener Vertrag ist kein ausführbarer Agent.
"""

def check(roles):
    missing=[]
    for r in roles:
        path=ROOT/"agents"/f"{r['id']}-{r['slug']}.md"
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
            continue
        content=path.read_text(encoding="utf-8")
        if not content.startswith(f"# Agent {r['id']}: {r['name']}"):
            raise ValueError(f"Agent contract mismatch: {path}")
    if missing:
        raise ValueError("Missing agent contracts: "+", ".join(missing))
    print("Registry and 38 agent contracts validated")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--write",action="store_true")
    p.add_argument("--check",action="store_true")
    args=p.parse_args()
    roles=load()
    if args.write:
        for r in roles:
            (ROOT/"agents"/f"{r['id']}-{r['slug']}.md").write_text(render(r),encoding="utf-8")
    check(roles)
if __name__=="__main__":
    main()
