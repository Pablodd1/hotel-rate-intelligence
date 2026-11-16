"""Competitor Pricing Memory, Behavioral Decision Pattern & Occupancy Pressure Estimator (`hri/memory_engine.py`).

ZERO-HALLUCINATION DESIGN:
- `history_timeline` is built STRICTLY from real rows recorded in `rates` (never MD5 wave backfills).
- `est_occupancy_pct` is explicitly labeled as an algorithmic market-compression index computed from
  real live OTA scarcity & recorded price band position unless verified by a logged courtesy call.
"""
import json
import time
from datetime import date


def estimate_occupancy_and_personality(hotel: dict, current_bar: float, prev_bar: float, ota_channels: list, undercut_pct: float):
    """Estimate algorithmic occupancy pressure index and classify pricing behavior from live signals."""
    if not current_bar:
        return {
            "est_occupancy_pct": int(hotel.get("est_occupancy_pct") or 70),
            "pricing_personality": "Awaiting Live Quote",
            "pattern_code": "NO_LIVE_QUOTE",
            "decision_logic": "No live OTA quote stored yet for this property/date.",
            "band_position_pct": 50,
            "price_min": round(float(hotel.get("price_min") or 0)),
            "price_max": round(float(hotel.get("price_max") or 0)),
        }

    p_min = float(hotel.get("price_min") or max(85, round(current_bar * 0.72)))
    p_max = float(hotel.get("price_max") or max(current_bar * 1.45, p_min + 100))
    span = max(25.0, p_max - p_min)
    band_pos = max(0.0, min(1.0, (current_bar - p_min) / span))

    num_otas = len(ota_channels or [])
    scarcity_boost = 8 if 0 < num_otas <= 2 else (4 if num_otas == 3 else 0)
    delta_pct = ((current_bar - prev_bar) / prev_bar * 100.0) if prev_bar else 0.0
    momentum_boost = round(max(-10.0, min(12.0, delta_pct * 0.8)))

    raw_occ = round(54 + (band_pos * 34) + scarcity_boost + momentum_boost)
    est_occ = max(42, min(97, int(raw_occ)))

    if undercut_pct <= -6.0:
        personality = "Passive Wholesale Leaker"
        pattern_code = "WHOLESALE_LEAK"
        decision_logic = (
            f"Live OTA undercut detected ({undercut_pct:+.1f}% vs benchmark retail BAR ${current_bar:.0f}). "
            f"Algorithmic pressure index ~{est_occ}% ({num_otas} live channels reporting)."
        )
    elif delta_pct >= 6.0 and est_occ >= 76:
        personality = "Early Compression Yielder"
        pattern_code = "AGGRESSIVE_YIELD"
        decision_logic = (
            f"Rate rose {delta_pct:+.1f}% across live scans to ${current_bar:.0f} (pressure index ~{est_occ}%)."
        )
    elif delta_pct <= -5.0 and est_occ < 70:
        personality = "Last-Minute Discounter"
        pattern_code = "DISCOUNT_DUMP"
        decision_logic = (
            f"Rate dropped {delta_pct:+.1f}% across live scans to ${current_bar:.0f} (pressure index ~{est_occ}%)."
        )
    else:
        personality = "Steady Tier Holder"
        pattern_code = "HOLD_STEADY"
        decision_logic = (
            f"Holding ${current_bar:.0f}/nt across live scans (pressure index ~{est_occ}%, band ${round(p_min)}-${round(p_max)})."
        )

    return {
        "est_occupancy_pct": est_occ,
        "pricing_personality": personality,
        "pattern_code": pattern_code,
        "decision_logic": decision_logic,
        "band_position_pct": round(band_pos * 100),
        "price_min": round(p_min),
        "price_max": round(p_max),
    }


def record_and_analyze_memory(conn, hotel_id: int) -> dict:
    """Retrieve strictly real memorized rate observations and competitor decisions for one hotel."""
    h_row = conn.execute("SELECT * FROM hotels WHERE id=?", (hotel_id,)).fetchone()
    if not h_row:
        return {}
    hotel = dict(h_row)

    rate_rows = [dict(r) for r in conn.execute(
        "SELECT * FROM rates WHERE hotel_id=? AND nightly_price IS NOT NULL ORDER BY scraped_at ASC, id ASC LIMIT 30",
        (hotel_id,),
    )]
    latest = rate_rows[-1] if rate_rows else {}
    prev = rate_rows[-2] if len(rate_rows) > 1 else {}

    cur_bar = round(float(latest["nightly_price"])) if latest.get("nightly_price") is not None else None
    prev_bar = round(float(prev["nightly_price"])) if prev.get("nightly_price") is not None else None
    delta_pct = round(((cur_bar - prev_bar) / prev_bar) * 100, 1) if (cur_bar and prev_bar) else 0.0
    undercut_pct = float(latest.get("undercut_pct") or 0.0)
    try:
        ota_channels = json.loads(latest.get("ota_json") or "[]")
    except Exception:
        ota_channels = []

    occ_intel = estimate_occupancy_and_personality(hotel, cur_bar or 0, prev_bar or (cur_bar or 0), ota_channels, undercut_pct)
    if cur_bar:
        conn.execute(
            "UPDATE hotels SET est_occupancy_pct=?, pricing_personality=? WHERE id=?",
            (occ_intel["est_occupancy_pct"], occ_intel["pricing_personality"], hotel_id),
        )

    # Strictly REAL recorded DB points — ZERO synthetic wave backfills
    history_points = []
    for idx, r in enumerate(rate_rows[-12:]):
        ts = r.get("scraped_at") or time.time()
        d_str = r.get("checkin") or (date.fromtimestamp(ts).strftime("%b %d") if ts else f"Run {idx+1}")
        p_val = round(float(r["nightly_price"]))
        u_pct = float(r.get("undercut_pct") or 0.0)
        try:
            r_otas = json.loads(r.get("ota_json") or "[]")
        except Exception:
            r_otas = []
        r_occ = estimate_occupancy_and_personality(hotel, p_val, p_val, r_otas, u_pct)["est_occupancy_pct"]
        history_points.append({
            "date": f"{d_str}",
            "bar": p_val,
            "ota_low": round(p_val * (1.0 + min(0.0, u_pct / 100.0))),
            "est_occupancy_pct": r_occ,
            "note": f"Real {r.get('source')} check-in {r.get('checkin')} ({r.get('parity_status')})",
        })

    comp_rows = [dict(r) for r in conn.execute("""
        SELECT h.id, h.name, h.area, h.stars, h.est_rooms, h.price_min, h.price_max, h.review_rating,
               (SELECT nightly_price FROM rates WHERE hotel_id=h.id AND nightly_price IS NOT NULL ORDER BY id DESC LIMIT 1) AS price,
               (SELECT nightly_price FROM rates WHERE hotel_id=h.id AND nightly_price IS NOT NULL ORDER BY id DESC LIMIT 1 OFFSET 1) AS prev_price,
               (SELECT undercut_pct FROM rates WHERE hotel_id=h.id AND nightly_price IS NOT NULL ORDER BY id DESC LIMIT 1) AS undercut_pct
        FROM hotels h
        WHERE h.id != ?
        ORDER BY (CASE WHEN h.area = ? THEN 0 ELSE 1 END),
                 ABS(COALESCE(h.stars, 3.8) - COALESCE(?, 3.8))
        LIMIT 5
    """, (hotel_id, hotel.get("area"), hotel.get("stars")))]

    competitor_decisions = []
    for c in comp_rows:
        if c.get("price") is None:
            continue
        cp = round(float(c["price"]))
        cpp = round(float(c["prev_price"])) if c.get("prev_price") is not None else cp
        cdelta = round(((cp - cpp) / cpp) * 100, 1) if cpp else 0.0
        cu = float(c.get("undercut_pct") or 0.0)
        c_occ = estimate_occupancy_and_personality(c, cp, cpp, [], cu)
        competitor_decisions.append({
            "hotel_id": c["id"],
            "name": c["name"],
            "area": c.get("area"),
            "bar": cp,
            "prev_bar": cpp,
            "delta_pct": cdelta,
            "undercut_pct": cu,
            "est_occupancy_pct": c_occ["est_occupancy_pct"],
            "personality": c_occ["pricing_personality"],
            "decision_summary": c_occ["decision_logic"],
        })

    comp_avg = round(sum(x["bar"] for x in competitor_decisions) / len(competitor_decisions)) if competitor_decisions else (cur_bar or 0)

    if not cur_bar:
        recommended_bar = comp_avg or None
        strategy_action = "NO LIVE QUOTE YET — RUN SCRAPE OR VERIFY XOTELO KEY"
        strategy_rationale = "Waiting for a live OTA quote before issuing a rate change recommendation."
    elif undercut_pct <= -2.0 and cur_bar > comp_avg * 1.05:
        recommended_bar = max(occ_intel["price_min"] or 90, round((cur_bar + comp_avg) / 2))
        strategy_action = f"CLOSE OTA LEAK & ALIGN BAR (${cur_bar} -> ${recommended_bar}/nt)"
        strategy_rationale = (
            f"Live quote shows a {undercut_pct:+.1f}% third-party OTA undercut while corridor neighbors average ${comp_avg}/nt."
        )
    elif cur_bar < comp_avg or occ_intel["est_occupancy_pct"] >= 76:
        lift = max(10, min(35, round((comp_avg - cur_bar) * 0.65) if comp_avg > cur_bar else round(cur_bar * 0.05)))
        recommended_bar = cur_bar + lift
        strategy_action = f"RAISE BAR +${lift}/NT (${cur_bar} -> ${recommended_bar}/nt)"
        strategy_rationale = (
            f"Corridor peers average ${comp_avg}/nt vs your live quote of ${cur_bar}/nt (pressure index ~{occ_intel['est_occupancy_pct']}%)."
        )
    else:
        nudge = max(8, round(cur_bar * 0.04))
        recommended_bar = cur_bar + nudge
        strategy_action = f"HOLD WEEKDAY (${cur_bar}) & LIFT FRI-SAT TO ${recommended_bar}/nt"
        strategy_rationale = f"Hold mid-week floor near ${cur_bar}/nt and lift weekends toward ${recommended_bar}/nt."

    existing_mem = conn.execute("SELECT COUNT(*) c FROM memory_events WHERE hotel_id=?", (hotel_id,)).fetchone()["c"]
    if existing_mem == 0 and cur_bar:
        conn.execute(
            """INSERT INTO memory_events(
               hotel_id, event_type, old_price, new_price, delta_pct,
               est_occupancy_pct, competitor_pattern, ai_recommendation, recorded_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                hotel_id,
                "strategy_decision",
                prev_bar,
                cur_bar,
                delta_pct,
                occ_intel["est_occupancy_pct"],
                occ_intel["pattern_code"],
                f"{strategy_action}: {strategy_rationale}",
                time.time(),
            ),
        )
    conn.commit()

    mem_logs = [dict(r) for r in conn.execute(
        "SELECT * FROM memory_events WHERE hotel_id=? ORDER BY id DESC LIMIT 10", (hotel_id,)
    )]

    return {
        "hotel_id": hotel_id,
        "hotel_name": hotel["name"],
        "area": hotel.get("area"),
        "current_bar": cur_bar,
        "prev_bar": prev_bar,
        "delta_pct": delta_pct,
        "comp_avg_bar": comp_avg,
        "recommended_bar": recommended_bar,
        "strategy_action": strategy_action,
        "strategy_rationale": strategy_rationale,
        "occupancy": occ_intel,
        "history_timeline": history_points,
        "competitor_decisions": competitor_decisions,
        "memory_logs": mem_logs,
    }
