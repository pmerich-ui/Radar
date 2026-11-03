"""Merge video ledger with current main and commit safely after concurrent GitHub edits."""
import json
import subprocess
from pathlib import Path

LEDGER = Path("data/produced.json")


def git(*args, check=True):
    return subprocess.run(["git", *args], text=True, capture_output=True, check=check)


def records(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["produced"]
    if not isinstance(rows, list):
        raise ValueError("Invalid produced ledger")
    return rows


def merge(remote_rows, local_rows):
    combined = []
    by_id = {}
    for row in [*remote_rows, *local_rows]:
        key = row["id"]
        if key in by_id:
            if by_id[key]["sha256"] != row["sha256"]:
                raise ValueError("Conflicting SHA256 for video id " + key)
            continue
        by_id[key] = row
        combined.append(row)
    return combined


def main():
    local_rows = records(LEDGER)
    for attempt in range(1, 6):
        git("fetch", "origin", "main")
        remote_result = git("show", "origin/main:data/produced.json", check=False)
        remote_rows = json.loads(remote_result.stdout)["produced"] if remote_result.returncode == 0 else []
        rows = merge(remote_rows, local_rows)
        LEDGER.write_text(json.dumps({"produced": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        local_rows = rows
        git("reset", "--mixed", "origin/main")
        git("add", "data/produced.json")
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            print("Ledger already current:", len(rows))
            return
        git("commit", "-m", "Record newly rendered original videos")
        attempt_push = git("push", "origin", "HEAD:main", check=False)
        if attempt_push.returncode == 0:
            print("Ledger saved:", len(rows))
            return
        if "rejected" not in attempt_push.stderr and "non-fast-forward" not in attempt_push.stderr:
            raise RuntimeError("Git push failed: " + attempt_push.stderr)
        print("Main moved during push; retrying ledger merge:", attempt)
    raise RuntimeError("Unable to save ledger after 5 merge-and-push attempts")


if __name__ == "__main__":
    main()
