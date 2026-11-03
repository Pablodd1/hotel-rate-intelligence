#!/usr/bin/env python3
"""Dump the dashboard's API payloads to JSON snapshots for serverless deploys.

The self-hosted server (hri/server.py) reads SQLite live. Vercel/serverless
has no persistent SQLite, so we commit these snapshots and api/index.py
serves them. Re-run after each collection, commit, and redeploy to refresh
the public dashboard.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from hri import db as dbmod
from hri.config import load
from hri.server import _summary, _hotels, _all_pitches


def main():
    cfg = load()
    conn = dbmod.open_db(cfg["database"])
    snapshots = (
        ("snapshot_summary", lambda c: _summary(c, cfg)),
        ("snapshot_hotels", lambda c: {"hotels": _hotels(c)}),
        ("snapshot_pitches", _all_pitches),
    )
    for name, fn in snapshots:
        payload = fn(conn)
        out_path = os.path.join(ROOT, "api", f"{name}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1, default=str)
        print(f"api/{name}.json  ({len(json.dumps(payload)):,} bytes)")
    conn.close()


if __name__ == "__main__":
    main()
