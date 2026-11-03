#!/usr/bin/env python3
"""Dump the dashboard's API payloads to JSON snapshots for serverless deploys.

The self-hosted server (hri/server.py) reads SQLite live. Vercel/serverless
has no persistent SQLite, so we commit these snapshots and api/index.py
serves them. Re-run after each collection, commit, and redeploy to refresh
the public dashboard.
"""
import json, sqlite3, sys

sys.path.insert(0, "/root/.openclaw/workspace/hotel-rate-intelligence")
from hri.config import load
from hri.server import _summary, _hotels


def main():
    cfg = load()
    conn = sqlite3.connect(cfg["database"])
    conn.row_factory = sqlite3.Row
    for name, fn in (("snapshot_summary", lambda c: _summary(c, cfg)), ("snapshot_hotels", _hotels)):
        payload = fn(conn)
        with open(f"api/{name}.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1, default=str)
        print(f"api/{name}.json  ({len(json.dumps(payload)):,} bytes)")
    conn.close()


if __name__ == "__main__":
    main()
