#!/usr/bin/env python3
"""Import a google-maps-scraper-kit CSV into HRI's `leads` table.

The Maps kit gives breadth (every hotel in the city, with phones/emails/socials);
the curated `hotels` comp set stays the 20-property deep-dive. `leads` is the
top-of-funnel for outreach.

Usage: python3 scripts/import_leads.py <csv> [--source-tag miami_beach_grid]
"""
import csv, json, sqlite3, sys, time

sys.path.insert(0, "/root/.openclaw/workspace/hotel-rate-intelligence")
from hri.config import load


def main():
    csv_path = sys.argv[1]
    tag = "gmaps_kit"
    if "--source-tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--source-tag") + 1]
    cfg = load()
    conn = sqlite3.connect(cfg["database"])
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL, phone TEXT, emails TEXT, website TEXT,
        category TEXT, address TEXT, rating REAL, review_count INTEGER,
        instagram TEXT, facebook TEXT, linkedin TEXT,
        place_id TEXT, source TEXT NOT NULL, imported_at REAL NOT NULL,
        UNIQUE(place_id, source))""")

    n, skipped = 0, 0
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                conn.execute("""INSERT OR IGNORE INTO leads
                    (name,phone,emails,website,category,address,rating,review_count,
                     instagram,facebook,linkedin,place_id,source,imported_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (row.get("title"), row.get("phone"), row.get("emails"),
                     row.get("website"), row.get("category"), row.get("address"),
                     float(row["review_rating"]) if row.get("review_rating") else None,
                     int(row["review_count"]) if row.get("review_count") else None,
                     row.get("instagram"), row.get("facebook"), row.get("linkedin"),
                     row.get("place_id") or row.get("title"), tag, time.time()))
                n += 1
            except Exception:
                skipped += 1
    conn.commit()
    stats = dict(conn.execute("SELECT COUNT(*) c, "
        "SUM(emails IS NOT NULL AND emails<>'') e, "
        "SUM(phone IS NOT NULL AND phone<>'') p, "
        "SUM(instagram IS NOT NULL AND instagram<>'') i FROM leads WHERE source=?", (tag,)).fetchone())
    conn.close()
    print(f"imported {n} rows ({skipped} skipped) — tag={tag}")
    print(f"with email: {stats['e']} · with phone: {stats['p']} · with instagram: {stats['i']}")


if __name__ == "__main__":
    main()
