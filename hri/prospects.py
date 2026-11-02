"""Prospect scoring — "understand who needs it".

Who buys hotel rate intelligence? Independent boutique hotels that:
  - are small/mid-size (roughly 20–120 rooms — big enough to care, too small for an in-house RMS team)
  - are independent (no brand revenue-management desk behind them)
  - sit in a dense competitive micro-market (many same-class neighbors within walking distance)
  - keep an active web presence but no obvious dynamic-pricing tooling
  - have a reachable decision-maker contact (GM / revenue / front desk)

Score 0..100 → tier hot (≥70) / warm (≥45) / watch. Fully heuristic, all
signals transparent and stored as JSON so a human can override.
"""
import json, time

WEIGHTS = {
    "independent": 25,     # no brand RMS
    "size_fit": 20,        # 20..120 est rooms (or unknown = 10)
    "midscale_stars": 15,  # 3–4.5 stars: most price-sensitive segment
    "dense_market": 15,    # ≥6 hotels in the same area string
    "contactable": 15,     # ≥1 email or phone captured
    "fresh_data": 10,      # ≥1 rate observation in the last 14 days
}


def score_all(conn, log=print):
    hotels = [dict(r) for r in conn.execute("SELECT * FROM hotels")]
    areas = {}
    for h in hotels:
        areas[h["area"] or "unknown"] = areas.get(h["area"] or "unknown", 0) + 1

    now = time.time()
    n = 0
    for h in hotels:
        signals, score = [], 0
        independent = (h["brand"] or "independent").lower() == "independent"
        if independent:
            score += WEIGHTS["independent"]; signals.append("independent — no brand RMS desk")
        rooms = h["est_rooms"]
        if rooms is None:
            score += 10; signals.append("size unknown (mid-market assumption)")
        elif 20 <= rooms <= 120:
            score += WEIGHTS["size_fit"]; signals.append(f"{rooms} rooms — right-size for outsourced intel")
        elif rooms < 200:
            score += 8; signals.append(f"{rooms} rooms — borderline")
        if h["stars"] and 3 <= h["stars"] <= 4.5:
            score += WEIGHTS["midscale_stars"]; signals.append(f"{h['stars']}★ — most price-sensitive segment")
        if areas.get(h["area"] or "unknown", 0) >= 6:
            score += WEIGHTS["dense_market"]; signals.append(f"dense micro-market ({h['area']})")
        has_contact = conn.execute(
            "SELECT 1 FROM contacts WHERE hotel_id=? LIMIT 1", (h["id"],)).fetchone()
        if has_contact:
            score += WEIGHTS["contactable"]; signals.append("decision-maker contact captured")
        fresh = conn.execute(
            "SELECT 1 FROM rates WHERE hotel_id=? AND scraped_at>? LIMIT 1",
            (h["id"], now - 14 * 86400)).fetchone()
        if fresh:
            score += WEIGHTS["fresh_data"]; signals.append("live rate data flowing")

        score = min(100, score)
        tier = "hot" if score >= 70 else ("warm" if score >= 45 else "watch")
        conn.execute(
            "INSERT INTO prospects(hotel_id,score,tier,signals,scored_at) VALUES(?,?,?,?,?)"
            " ON CONFLICT(hotel_id) DO UPDATE SET score=excluded.score, tier=excluded.tier,"
            " signals=excluded.signals, scored_at=excluded.scored_at",
            (h["id"], score, tier, json.dumps(signals), now))
        n += 1
    conn.commit()
    log(f"  prospects scored: {n} hotels")
    return n
