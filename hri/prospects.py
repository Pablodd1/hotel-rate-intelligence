"""Prospect scoring — "understand who needs it" + Annual Revenue Recovery Calculator.

Who buys hotel rate intelligence? Independent boutique hotels that:
  - are small/mid-size (roughly 20–150 rooms — big enough to care, too small for an in-house RMS team)
  - are independent (no brand revenue-management desk behind them)
  - sit in a dense competitive micro-market (many same-class neighbors within walking distance)
  - suffer from wholesale/OTA rate parity undercuts (Agoda/Booking undercutting Direct BAR)
  - have a reachable decision-maker contact (GM / revenue / sales / front desk)

Score 0..100 → tier hot (≥70) / warm (≥45) / watch. Fully heuristic, all
signals transparent and stored as JSON so a human can override.
"""
import json, time

WEIGHTS = {
    "independent": 25,     # no brand RMS
    "size_fit": 20,        # 20..135 est rooms (or unknown = 10)
    "midscale_stars": 15,  # 3–4.5 stars: most price-sensitive segment
    "dense_market": 15,    # ≥5 hotels in the same area string
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
            score += WEIGHTS["independent"]
            signals.append("independent — no corporate brand RMS desk")
        rooms = h["est_rooms"]
        if rooms is None:
            score += 10
            signals.append("size unknown (mid-market assumption)")
        elif 20 <= rooms <= 135:
            score += WEIGHTS["size_fit"]
            signals.append(f"{rooms} rooms — sweet-spot for outsourced rate intel")
        elif rooms < 220:
            score += 10
            signals.append(f"{rooms} rooms — mid-size boutique")
        if h["stars"] and 3 <= h["stars"] <= 4.5:
            score += WEIGHTS["midscale_stars"]
            signals.append(f"{h['stars']}★ — high price-sensitivity comp tier")
        if areas.get(h["area"] or "unknown", 0) >= 5:
            score += WEIGHTS["dense_market"]
            signals.append(f"dense micro-market ({h['area']})")
        has_contact = conn.execute(
            "SELECT 1 FROM contacts WHERE hotel_id=? LIMIT 1", (h["id"],)).fetchone()
        if has_contact:
            score += WEIGHTS["contactable"]
            signals.append("verified decision-maker contacts captured")
        latest_rate = conn.execute(
            "SELECT nightly_price, parity_status, undercut_pct FROM rates WHERE hotel_id=? AND scraped_at>? ORDER BY id DESC LIMIT 1",
            (h["id"], now - 14 * 86400)).fetchone()
        adr = 260.0
        if latest_rate:
            score += WEIGHTS["fresh_data"]
            adr = float(latest_rate["nightly_price"] or 260.0)
            if latest_rate["parity_status"] == "UNDERCUT":
                score = min(100, score + 6)
                signals.append(f"OTA parity leak ({latest_rate['undercut_pct']:+.1f}% undercut vs BAR)")
            else:
                signals.append("live multi-OTA rate data flowing")

        # Estimate annual revenue recovery (72% occupancy, 6% RevPAR + direct shift lift)
        eff_rooms = min(220, max(25, int(rooms or 65)))
        est_annual_upside = int(round(eff_rooms * 365 * 0.72 * adr * 0.055, -2))

        score = min(100, score)
        tier = "hot" if score >= 70 else ("warm" if score >= 45 else "watch")
        conn.execute(
            "INSERT INTO prospects(hotel_id,score,tier,signals,est_annual_upside,scored_at) VALUES(?,?,?,?,?,?)"
            " ON CONFLICT(hotel_id) DO UPDATE SET score=excluded.score, tier=excluded.tier,"
            " signals=excluded.signals, est_annual_upside=excluded.est_annual_upside, scored_at=excluded.scored_at",
            (h["id"], score, tier, json.dumps(signals), est_annual_upside, now))
        n += 1
    conn.commit()
    log(f"  prospects scored: {n} hotels")
    return n
