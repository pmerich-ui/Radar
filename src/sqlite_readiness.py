"""Check durable SQLite configuration when Supabase is not used.

No deployment or publishing side effects. SQLite requires one writer service
and a persistent mounted directory; ephemeral CI runners are not durable.
"""
import os
from pathlib import Path

def sqlite_readiness(environ=None):
    env = os.environ if environ is None else environ
    problems = []
    db = env.get("LEDGER_SQLITE_PATH", "")
    mount = env.get("LEDGER_PERSISTENT_DIR", "")
    if not db or not Path(db).is_absolute():
        problems.append("LEDGER_SQLITE_PATH must be absolute")
    if not mount or not Path(mount).is_absolute():
        problems.append("LEDGER_PERSISTENT_DIR must be an absolute persistent volume mount")
    if db and mount and Path(db).is_absolute() and Path(mount).is_absolute():
        if not Path(db).resolve().is_relative_to(Path(mount).resolve()):
            problems.append("SQLite database must reside under persistent mount")
    if env.get("LEDGER_SINGLE_WRITER", "").lower() != "true":
        problems.append("SQLite requires an explicitly configured single writer service")
    if env.get("LEDGER_BACKUP_ENABLED", "").lower() != "true":
        problems.append("Persistent backups are required")
    return problems

def require_sqlite_readiness(environ=None):
    issues = sqlite_readiness(environ)
    if issues:
        raise RuntimeError("; ".join(issues))
