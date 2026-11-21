"""Reservations Operations Console, Room Inventory (OOO/OOS/Housekeeping),
AI Auto-Pricing Strategy Engine, Telegram Operational Alerts, and Competitor Email Inquiry Desk.

Built for real boutique hotel Reservations & Front Office teams:
- Tracks real-time inventory disruptions: Out of Order (OOO), Out of Service (OOS),
  Housekeeping shortages, Sold Out / Stop-Sell / CTA / Min-LOS, and room-type switches.
- Recalculates True Sellable Inventory and Net Occupancy % immediately.
- Feeds live operational reality + scraped comp-set rates into the AI Auto-Pricing Engine.
- Dispatches tagged Telegram alerts (#OOO, #Housekeeping, #Compression, #ParityLeak).
- Supports Competitor Rate Inquiry emails alongside the Overnight Courtesy Call-Around Desk.
"""
import json
import time
from datetime import date, timedelta

from . import db as dbmod
from .report import send_telegram


DEFAULT_STATUS_FLAGS = [
    {"id": "SOLD_OUT", "label": "Sold Out (Stop-Sell All)"},
    {"id": "STOP_SELL_OTA", "label": "Close Discount OTAs (Direct Only)"},
    {"id": "CTA", "label": "Closed to Arrival (CTA)"},
    {"id": "MIN_LOS_2", "label": "2-Night Min Stay (Min-LOS)"},
    {"id": "HOUSEKEEPING_SHORT", "label": "Housekeeping Short-Staffed"},
    {"id": "MAINTENANCE_ISSUE", "label": "AC / Plumbing Maintenance Active"},
]

DEFAULT_OPS_TAGS = [
    "#OOO",
    "#OOS",
    "#Housekeeping",
    "#Compression",
    "#ParityLeak",
    "#NightAudit",
    "#WalkInOnly",
    "#RoomSwitch",
]

INQUIRY_TEMPLATES = {
    "courtesy_rate_swap": {
        "label": "Front-Desk Courtesy Rate & Occupancy Swap",
        "subject": "Quick Miami Beach neighbor check — tonight's availability & BAR",
        "body_tpl": (
            "Hi {target_name} Reservations / Front Desk Team,\n\n"
            "This is the Reservations Desk at {my_name} right down the corridor in {area}. "
            "We are updating our daily local walk-in referral list for {checkin} in case either of us sells out tonight.\n\n"
            "Could you share your current walk-in BAR and whether you have availability for {rooms} room(s)? "
            "Happy to share ours and send overflow guests your way whenever we hit 100%.\n\n"
            "Thank you — supporting our local Miami Beach neighbors,\n"
            "{my_name} Reservations Team"
        ),
    },
    "group_overflow_check": {
        "label": "Overflow / Small Group Rate Inquiry",
        "subject": "Availability & rate check for {rooms} rooms ({checkin})",
        "body_tpl": (
            "Hello {target_name} Team,\n\n"
            "We have guests looking for {rooms} room(s) checking in {checkin} in {area} and want to verify "
            "current direct best available rates and any resort fee / minimum stay requirements.\n\n"
            "Could you reply with your available room categories and out-the-door nightly rate?\n\n"
            "Best regards,\n"
            "Reservations Inquiry · {area}"
        ),
    },
}


def _default_room_types(total_rooms: int, base_bar: float) -> list:
    total = max(5, int(total_rooms or 45))
    bar = max(79.0, float(base_bar or 199.0))
    std_cnt = max(2, round(total * 0.45))
    king_cnt = max(2, round(total * 0.35))
    suite_cnt = max(1, total - std_cnt - king_cnt)
    return [
        {
            "code": "STDQ",
            "name": "Standard Queen",
            "total": std_cnt,
            "ooo": 0,
            "oos": 0,
            "bar": round(bar),
            "stop_sell": False,
        },
        {
            "code": "DLXK",
            "name": "Deluxe King",
            "total": king_cnt,
            "ooo": 0,
            "oos": 0,
            "bar": round(bar * 1.15),
            "stop_sell": False,
        },
        {
            "code": "SUIT",
            "name": "Boutique / Ocean Suite",
            "total": suite_cnt,
            "ooo": 0,
            "oos": 0,
            "bar": round(bar * 1.48),
            "stop_sell": False,
        },
    ]


def _latest_hotel_rate(conn, hotel_id: int) -> dict:
    row = conn.execute(
        """SELECT nightly_price, ota_json, parity_status, undercut_pct, checkin, scraped_at
           FROM rates WHERE hotel_id=? ORDER BY scraped_at DESC LIMIT 1""",
        (hotel_id,),
    ).fetchone()
    if not row:
        return {"nightly_price": 199.0, "ota_channels": [], "parity_status": "PARITY", "undercut_pct": 0.0}
    d = dict(row)
    try:
        d["ota_channels"] = json.loads(d.get("ota_json") or "[]")
    except Exception:
        d["ota_channels"] = []
    return d


def get_or_init_room_ops(conn, hotel_id: int) -> dict:
    row = conn.execute("SELECT * FROM room_inventory_ops WHERE hotel_id=?", (hotel_id,)).fetchone()
    if row:
        ops = dict(row)
    else:
        h = conn.execute("SELECT id, name, est_rooms, est_occupancy_pct FROM hotels WHERE id=?", (hotel_id,)).fetchone()
        total = int((h["est_rooms"] if h and h["est_rooms"] else 45))
        occ_pct = int((h["est_occupancy_pct"] if h and h["est_occupancy_pct"] else 74))
        sold = max(0, min(total, round(total * occ_pct / 100.0)))
        latest = _latest_hotel_rate(conn, hotel_id)
        base_bar = float(latest.get("nightly_price") or 199.0)
        room_types = _default_room_types(total, base_bar)
        now = time.time()
        conn.execute(
            """INSERT OR IGNORE INTO room_inventory_ops
               (hotel_id, total_rooms, rooms_sold, ooo_rooms, oos_rooms, housekeeping_hold,
                status_flags, operational_tags, room_types_json, notes, updated_by, updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                hotel_id, total, sold, 0, 0, 0,
                "[]", json.dumps(["#NightAudit"]), json.dumps(room_types),
                "Initial inventory synced from property profile. Update OOO/OOS/Housekeeping anytime.",
                "System Sync", now,
            ),
        )
        conn.commit()
        ops = dict(conn.execute("SELECT * FROM room_inventory_ops WHERE hotel_id=?", (hotel_id,)).fetchone())

    return _enrich_room_ops(ops)


def _enrich_room_ops(ops: dict) -> dict:
    total = max(1, int(ops.get("total_rooms") or 1))
    ooo = max(0, int(ops.get("ooo_rooms") or 0))
    oos = max(0, int(ops.get("oos_rooms") or 0))
    hk = max(0, int(ops.get("housekeeping_hold") or 0))
    offline = min(total, ooo + oos + hk)
    sellable = max(0, total - offline)
    sold = max(0, min(total, int(ops.get("rooms_sold") or 0)))
    remaining = max(0, sellable - sold)

    gross_occ = round((sold / total) * 100.0, 1)
    net_occ = 100.0 if sellable == 0 else round(min(100.0, (sold / sellable) * 100.0), 1)

    try:
        flags = json.loads(ops.get("status_flags") or "[]")
    except Exception:
        flags = []
    try:
        tags = json.loads(ops.get("operational_tags") or "[]")
    except Exception:
        tags = []
    try:
        room_types = json.loads(ops.get("room_types_json") or "[]")
    except Exception:
        room_types = []

    return {
        "hotel_id": ops["hotel_id"],
        "total_rooms": total,
        "rooms_sold": sold,
        "ooo_rooms": ooo,
        "oos_rooms": oos,
        "housekeeping_hold": hk,
        "offline_rooms": offline,
        "sellable_rooms": sellable,
        "remaining_to_sell": remaining,
        "gross_occupancy_pct": gross_occ,
        "net_occupancy_pct": net_occ,
        "occupancy_compression_delta": round(net_occ - gross_occ, 1),
        "status_flags": flags,
        "operational_tags": tags,
        "room_types": room_types,
        "notes": ops.get("notes") or "",
        "updated_by": ops.get("updated_by") or "Reservations Desk",
        "updated_at": ops.get("updated_at") or time.time(),
    }


def update_room_ops(conn, hotel_id: int, payload: dict, updated_by: str = "Reservations Desk") -> dict:
    cur = get_or_init_room_ops(conn, hotel_id)
    room_types = payload.get("room_types")
    if isinstance(room_types, list) and len(room_types) > 0:
        clean_rt = []
        rt_total_sum = 0
        rt_ooo_sum = 0
        rt_oos_sum = 0
        for idx, rt in enumerate(room_types):
            t_cnt = max(0, int(rt.get("total") or 0))
            t_ooo = max(0, min(t_cnt, int(rt.get("ooo") or 0)))
            t_oos = max(0, min(t_cnt - t_ooo, int(rt.get("oos") or 0)))
            clean_rt.append({
                "code": str(rt.get("code") or f"RM{idx+1}")[:8].upper(),
                "name": str(rt.get("name") or f"Room Type {idx+1}")[:48],
                "total": t_cnt,
                "ooo": t_ooo,
                "oos": t_oos,
                "bar": round(max(49.0, float(rt.get("bar") or 189.0)), 2),
                "stop_sell": bool(rt.get("stop_sell")),
            })
            rt_total_sum += t_cnt
            rt_ooo_sum += t_ooo
            rt_oos_sum += t_oos
        total_rooms = int(payload.get("total_rooms") or rt_total_sum or cur["total_rooms"])
        ooo_rooms = int(payload["ooo_rooms"]) if "ooo_rooms" in payload and payload["ooo_rooms"] is not None else rt_ooo_sum
        oos_rooms = int(payload["oos_rooms"]) if "oos_rooms" in payload and payload["oos_rooms"] is not None else rt_oos_sum
    else:
        clean_rt = cur["room_types"]
        total_rooms = max(1, int(payload.get("total_rooms", cur["total_rooms"])))
        ooo_rooms = max(0, int(payload.get("ooo_rooms", cur["ooo_rooms"])))
        oos_rooms = max(0, int(payload.get("oos_rooms", cur["oos_rooms"])))

    rooms_sold = max(0, int(payload.get("rooms_sold", cur["rooms_sold"])))
    hk_hold = max(0, int(payload.get("housekeeping_hold", cur["housekeeping_hold"])))
    flags = payload.get("status_flags", cur["status_flags"])
    if not isinstance(flags, list):
        flags = cur["status_flags"]
    tags = payload.get("operational_tags", cur["operational_tags"])
    if not isinstance(tags, list):
        tags = cur["operational_tags"]
    notes = str(payload.get("notes", cur["notes"]))[:600]
    now = time.time()

    conn.execute(
        """INSERT OR REPLACE INTO room_inventory_ops
           (hotel_id, total_rooms, rooms_sold, ooo_rooms, oos_rooms, housekeeping_hold,
            status_flags, operational_tags, room_types_json, notes, updated_by, updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            hotel_id, total_rooms, rooms_sold, ooo_rooms, oos_rooms, hk_hold,
            json.dumps(flags), json.dumps(tags), json.dumps(clean_rt),
            notes, updated_by, now,
        ),
    )
    # Keep hotels.est_rooms in sync if property total rooms changed
    conn.execute("UPDATE hotels SET est_rooms=? WHERE id=?", (total_rooms, hotel_id))
    conn.commit()
    return get_or_init_room_ops(conn, hotel_id)


def get_or_init_auto_pricing_rules(conn, hotel_id: int) -> dict:
    row = conn.execute("SELECT * FROM auto_pricing_rules WHERE hotel_id=?", (hotel_id,)).fetchone()
    if row:
        d = dict(row)
    else:
        latest = _latest_hotel_rate(conn, hotel_id)
        bar = float(latest.get("nightly_price") or 199.0)
        floor_p = max(79.0, round(bar * 0.72))
        ceil_p = max(floor_p + 120.0, round(bar * 2.25))
        now = time.time()
        conn.execute(
            """INSERT OR IGNORE INTO auto_pricing_rules
               (hotel_id, mode, min_bar_floor, max_bar_ceiling, compression_occ_threshold,
                compression_lift_pct, parity_auto_protect, comp_position_target,
                telegram_alerts_enabled, telegram_chat_id, alert_tags, updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                hotel_id, "semi_auto", floor_p, ceil_p, 85, 12.0, 1, "match_avg",
                1, "", json.dumps(["#OOO", "#ParityLeak", "#Compression", "#Housekeeping"]), now,
            ),
        )
        conn.commit()
        d = dict(conn.execute("SELECT * FROM auto_pricing_rules WHERE hotel_id=?", (hotel_id,)).fetchone())
    try:
        d["alert_tags"] = json.loads(d.get("alert_tags") or "[]")
    except Exception:
        d["alert_tags"] = ["#OOO", "#ParityLeak", "#Compression"]
    return d


def update_auto_pricing_rules(conn, hotel_id: int, payload: dict) -> dict:
    cur = get_or_init_auto_pricing_rules(conn, hotel_id)
    mode = payload.get("mode", cur["mode"])
    if mode not in ("advisory", "semi_auto", "auto_pilot"):
        mode = "semi_auto"
    min_floor = max(49.0, float(payload.get("min_bar_floor", cur["min_bar_floor"])))
    max_ceil = max(min_floor + 20.0, float(payload.get("max_bar_ceiling", cur["max_bar_ceiling"])))
    comp_thr = max(50, min(99, int(payload.get("compression_occ_threshold", cur["compression_occ_threshold"]))))
    comp_lift = max(2.0, min(50.0, float(payload.get("compression_lift_pct", cur["compression_lift_pct"]))))
    parity_prot = 1 if payload.get("parity_auto_protect", cur["parity_auto_protect"]) else 0
    comp_pos = payload.get("comp_position_target", cur["comp_position_target"])
    if comp_pos not in ("match_avg", "below_avg_5pct", "above_avg_5pct"):
        comp_pos = "match_avg"
    tg_on = 1 if payload.get("telegram_alerts_enabled", cur["telegram_alerts_enabled"]) else 0
    tg_chat = str(payload.get("telegram_chat_id", cur.get("telegram_chat_id") or "")).strip()
    alert_tags = payload.get("alert_tags", cur.get("alert_tags") or [])
    if not isinstance(alert_tags, list):
        alert_tags = cur.get("alert_tags") or []

    conn.execute(
        """INSERT OR REPLACE INTO auto_pricing_rules
           (hotel_id, mode, min_bar_floor, max_bar_ceiling, compression_occ_threshold,
            compression_lift_pct, parity_auto_protect, comp_position_target,
            telegram_alerts_enabled, telegram_chat_id, alert_tags, updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            hotel_id, mode, min_floor, max_ceil, comp_thr, comp_lift,
            parity_prot, comp_pos, tg_on, tg_chat, json.dumps(alert_tags), time.time(),
        ),
    )
    conn.commit()
    return get_or_init_auto_pricing_rules(conn, hotel_id)


def compute_ai_pricing_plan(conn, hotel_id: int, comp_hotel_ids: list = None) -> dict:
    """Compute a complete, transparent AI Auto-Pricing & Channel Strategy decision
    combining scraped comp-set rates, OTA parity, and live OOO/OOS/Housekeeping room inventory.
    """
    h_row = conn.execute("SELECT * FROM hotels WHERE id=?", (hotel_id,)).fetchone()
    hotel = dict(h_row) if h_row else {"id": hotel_id, "name": f"Hotel #{hotel_id}", "area": "Miami Beach"}
    ops = get_or_init_room_ops(conn, hotel_id)
    rules = get_or_init_auto_pricing_rules(conn, hotel_id)
    latest = _latest_hotel_rate(conn, hotel_id)
    current_bar = float(latest.get("nightly_price") or 199.0)

    # Comp-set average from assigned competitors (or area neighbors)
    if comp_hotel_ids:
        placeholders = ",".join("?" for _ in comp_hotel_ids)
        comp_rows = conn.execute(
            f"""SELECT h.id, h.name, r.nightly_price
                FROM hotels h
                JOIN (SELECT hotel_id, nightly_price, MAX(scraped_at) FROM rates GROUP BY hotel_id) r
                  ON r.hotel_id = h.id
                WHERE h.id IN ({placeholders}) AND h.id != ? AND r.nightly_price IS NOT NULL""",
            tuple(comp_hotel_ids) + (hotel_id,),
        ).fetchall()
    else:
        comp_rows = conn.execute(
            """SELECT h.id, h.name, r.nightly_price
               FROM hotels h
               JOIN (SELECT hotel_id, nightly_price, MAX(scraped_at) FROM rates GROUP BY hotel_id) r
                 ON r.hotel_id = h.id
               WHERE h.id != ? AND r.nightly_price IS NOT NULL
               ORDER BY CASE WHEN h.area=? THEN 0 ELSE 1 END LIMIT 8""",
            (hotel_id, hotel.get("area") or "Miami Beach"),
        ).fetchall()

    comp_prices = [float(r["nightly_price"]) for r in comp_rows if r["nightly_price"]]
    comp_avg = round(sum(comp_prices) / len(comp_prices), 2) if comp_prices else current_bar

    target_bar = current_bar
    reasons = []
    trigger_tags = list(ops.get("operational_tags") or [])
    channel_directive = "OPEN_ALL_CHANNELS"
    action_verdict = "HOLD_BAR"

    # 1. Room inventory / OOO / OOS / Housekeeping compression logic
    net_occ = float(ops["net_occupancy_pct"])
    flags = set(ops.get("status_flags") or [])

    if "SOLD_OUT" in flags or ops["remaining_to_sell"] <= 0:
        channel_directive = "STOP_SELL_ALL_OTAS"
        action_verdict = "STOP_SELL_SOLD_OUT"
        target_bar = min(rules["max_bar_ceiling"], round(current_bar * 1.25))
        reasons.append(
            f"0 sellable rooms left ({ops['ooo_rooms']} OOO, {ops['oos_rooms']} OOS, {ops['housekeeping_hold']} Housekeeping Hold). "
            "Trigger immediate Stop-Sell across OTAs to prevent oversell walk costs."
        )
        if "#SoldOut" not in trigger_tags:
            trigger_tags.append("#SoldOut")
    elif net_occ >= float(rules["compression_occ_threshold"]) or ops["remaining_to_sell"] <= 3:
        lift = float(rules["compression_lift_pct"]) / 100.0
        target_bar = round(max(current_bar * (1.0 + lift), comp_avg * 1.05))
        channel_directive = "CLOSE_DISCOUNT_OTAS_DIRECT_ONLY"
        action_verdict = "RAISE_BAR_COMPRESSION"
        if ops["offline_rooms"] > 0:
            reasons.append(
                f"Inventory Alert: {ops['offline_rooms']} offline rooms ({ops['ooo_rooms']} OOO / {ops['oos_rooms']} OOS / "
                f"{ops['housekeeping_hold']} Housekeeping) reduced sellable inventory to {ops['sellable_rooms']} rooms, "
                f"pushing true occupancy from {ops['gross_occupancy_pct']}% to {net_occ}%."
            )
            if "#OOO" not in trigger_tags and ops["ooo_rooms"] > 0:
                trigger_tags.append("#OOO")
            if "#Housekeeping" not in trigger_tags and ops["housekeeping_hold"] > 0:
                trigger_tags.append("#Housekeeping")
        reasons.append(
            f"Compression threshold ({rules['compression_occ_threshold']}%) crossed with {ops['remaining_to_sell']} rooms left -> "
            f"raise Direct BAR +{rules['compression_lift_pct']:.0f}% and close discount OTA allocations."
        )
        if "#Compression" not in trigger_tags:
            trigger_tags.append("#Compression")
    else:
        # 2. Comp-set positioning rule
        pos_mult = 1.0
        if rules["comp_position_target"] == "below_avg_5pct":
            pos_mult = 0.95
        elif rules["comp_position_target"] == "above_avg_5pct":
            pos_mult = 1.05
        desired_comp_bar = round(comp_avg * pos_mult)
        diff = desired_comp_bar - current_bar
        if diff >= 8:
            target_bar = round(current_bar + min(diff, current_bar * 0.12))
            action_verdict = "RAISE_BAR_TO_MARKET"
            reasons.append(
                f"Comp-set avg is ${comp_avg:.0f}/nt vs your ${current_bar:.0f}/nt BAR. "
                f"Nudge BAR up to ${target_bar:.0f}/nt to capture corridor ADR without losing pace."
            )
        elif diff <= -15 and net_occ < 60:
            target_bar = round(current_bar - min(abs(diff), current_bar * 0.08))
            action_verdict = "TACTICAL_PACE_DROP"
            reasons.append(
                f"Net occupancy is {net_occ}% and BAR (${current_bar:.0f}) sits ${abs(diff):.0f} above comp avg (${comp_avg:.0f}). "
                f"Trim BAR slightly to ${target_bar:.0f}/nt to stimulate direct pickup."
            )
        else:
            reasons.append(
                f"Net occupancy ({net_occ}%, {ops['remaining_to_sell']} rooms left) and BAR (${current_bar:.0f}) are well-aligned with corridor avg (${comp_avg:.0f})."
            )

    # 3. OTA Parity Check
    parity_status = latest.get("parity_status") or "PARITY"
    undercut_pct = float(latest.get("undercut_pct") or 0.0)
    if parity_status == "UNDERCUT" and rules.get("parity_auto_protect"):
        if "#ParityLeak" not in trigger_tags:
            trigger_tags.append("#ParityLeak")
        reasons.append(
            f"Active OTA Parity Undercut ({undercut_pct:+.1f}%) detected -> issue wholesaler cease-undercut ticket & protect direct checkout."
        )
        if action_verdict == "HOLD_BAR":
            action_verdict = "FIX_PARITY_LEAK"

    # Respect guardrails (floor & ceiling)
    target_bar = round(max(float(rules["min_bar_floor"]), min(float(rules["max_bar_ceiling"]), target_bar)))
    delta_dollars = round(target_bar - current_bar, 2)
    delta_pct = round((delta_dollars / max(1.0, current_bar)) * 100.0, 1)

    # Compute per-room-type recommended prices
    ratio = target_bar / max(1.0, current_bar)
    room_recommendations = []
    for rt in ops.get("room_types") or []:
        cur_p = float(rt.get("bar") or current_bar)
        rec_p = round(max(float(rules["min_bar_floor"]), min(float(rules["max_bar_ceiling"]) * 1.6, cur_p * ratio)))
        avail = max(0, int(rt.get("total") or 0) - int(rt.get("ooo") or 0) - int(rt.get("oos") or 0))
        room_recommendations.append({
            "code": rt["code"],
            "name": rt["name"],
            "total": rt["total"],
            "ooo": rt.get("ooo", 0),
            "oos": rt.get("oos", 0),
            "sellable": avail,
            "current_bar": round(cur_p),
            "recommended_bar": rec_p,
            "delta": round(rec_p - cur_p),
            "stop_sell": bool(rt.get("stop_sell")) or avail == 0 or channel_directive == "STOP_SELL_ALL_OTAS",
        })

    pms_payload = {
        "property_id": hotel_id,
        "property_name": hotel.get("name"),
        "booking_engine": hotel.get("booking_engine") or "Direct / SynXis",
        "effective_date": date.today().isoformat(),
        "channel_directive": channel_directive,
        "new_base_bar": target_bar,
        "room_rates": [
            {"room_code": r["code"], "rate_usd": r["recommended_bar"], "stop_sell": r["stop_sell"]}
            for r in room_recommendations
        ],
    }

    recent_actions = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM pricing_actions_log WHERE hotel_id=? ORDER BY created_at DESC LIMIT 12",
            (hotel_id,),
        )
    ]

    return {
        "hotel_id": hotel_id,
        "hotel_name": hotel.get("name"),
        "current_bar": round(current_bar),
        "recommended_bar": target_bar,
        "delta_dollars": delta_dollars,
        "delta_pct": delta_pct,
        "comp_avg": round(comp_avg),
        "action_verdict": action_verdict,
        "channel_directive": channel_directive,
        "reasons": reasons,
        "trigger_tags": trigger_tags,
        "ops": ops,
        "rules": rules,
        "room_recommendations": room_recommendations,
        "pms_payload": pms_payload,
        "recent_actions": recent_actions,
        "status_flag_catalog": DEFAULT_STATUS_FLAGS,
        "default_ops_tags": DEFAULT_OPS_TAGS,
    }


def apply_ai_pricing_action(conn, cfg: dict, hotel_id: int, payload: dict = None) -> dict:
    payload = payload or {}
    plan = compute_ai_pricing_plan(conn, hotel_id)
    new_bar = round(float(payload.get("new_bar") or plan["recommended_bar"]))
    old_bar = plan["current_bar"]
    reason = payload.get("reason") or " | ".join(plan["reasons"])
    tags = payload.get("tags") or plan["trigger_tags"]
    now = time.time()

    # Log to pricing_actions_log
    conn.execute(
        """INSERT INTO pricing_actions_log
           (hotel_id, room_category, old_bar, new_bar, sellable_rooms, net_occupancy_pct,
            trigger_tags, reason, action_status, pms_payload, created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            hotel_id,
            payload.get("room_category") or "All Room Types (BAR)",
            old_bar,
            new_bar,
            plan["ops"]["sellable_rooms"],
            plan["ops"]["net_occupancy_pct"],
            json.dumps(tags),
            reason,
            "applied",
            json.dumps(plan["pms_payload"]),
            now,
        ),
    )

    # Also record in memory_events so the timeline shows the strategy move
    delta_pct = round(((new_bar - old_bar) / max(1.0, old_bar)) * 100.0, 1)
    conn.execute(
        """INSERT INTO memory_events
           (hotel_id, event_type, old_price, new_price, delta_pct, est_occupancy_pct,
            competitor_pattern, ai_recommendation, recorded_at)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            hotel_id,
            "strategy_decision",
            old_bar,
            new_bar,
            delta_pct,
            round(plan["ops"]["net_occupancy_pct"]),
            plan["action_verdict"],
            reason[:380],
            now,
        ),
    )

    # Update room_types_json BARs to reflect applied pricing
    updated_rt = []
    for r in plan["room_recommendations"]:
        updated_rt.append({
            "code": r["code"],
            "name": r["name"],
            "total": r["total"],
            "ooo": r["ooo"],
            "oos": r["oos"],
            "bar": r["recommended_bar"],
            "stop_sell": r["stop_sell"],
        })
    conn.execute(
        "UPDATE room_inventory_ops SET room_types_json=?, updated_at=? WHERE hotel_id=?",
        (json.dumps(updated_rt), now, hotel_id),
    )
    conn.commit()

    # Build Telegram Ops Alert
    tg_text = (
        f"HotelRateIntel OPS ALERT · {plan['hotel_name']}\n"
        f"Tags: {' '.join(tags)}\n"
        f"BAR Move: ${old_bar} -> ${new_bar} ({delta_pct:+.1f}%) | Directive: {plan['channel_directive']}\n"
        f"Inventory: {plan['ops']['sellable_rooms']}/{plan['ops']['total_rooms']} sellable "
        f"(OOO: {plan['ops']['ooo_rooms']} · OOS: {plan['ops']['oos_rooms']} · HK Hold: {plan['ops']['housekeeping_hold']})\n"
        f"Net Occupancy: {plan['ops']['net_occupancy_pct']}% ({plan['ops']['remaining_to_sell']} rooms left)\n"
        f"Reason: {reason[:220]}"
    )

    tg_sent = False
    if payload.get("send_telegram", True) and plan["rules"].get("telegram_alerts_enabled"):
        tg_cfg = dict(cfg)
        custom_chat = (plan["rules"].get("telegram_chat_id") or "").strip()
        if custom_chat:
            tg_block = dict(cfg.get("telegram") or {})
            tg_block["chat_id"] = custom_chat
            tg_cfg["telegram"] = tg_block
        tg_sent = send_telegram(tg_cfg, tg_text)

    return {
        "ok": True,
        "old_bar": old_bar,
        "new_bar": new_bar,
        "delta_pct": delta_pct,
        "telegram_sent": tg_sent,
        "telegram_preview": tg_text,
        "plan": compute_ai_pricing_plan(conn, hotel_id),
    }


def send_custom_telegram_ops_alert(conn, cfg: dict, hotel_id: int, message: str = "", tags: list = None) -> dict:
    plan = compute_ai_pricing_plan(conn, hotel_id)
    ops = plan["ops"]
    tag_str = " ".join(tags if isinstance(tags, list) and tags else (ops.get("operational_tags") or ["#OpsAlert"]))
    body = (
        f"HotelRateIntel SHIFT ALERT · {plan['hotel_name']}\n"
        f"Tags: {tag_str}\n"
        f"Rooms: {ops['rooms_sold']} sold / {ops['sellable_rooms']} sellable (Total {ops['total_rooms']} · "
        f"OOO {ops['ooo_rooms']} · OOS {ops['oos_rooms']} · HK {ops['housekeeping_hold']})\n"
        f"Net Occ: {ops['net_occupancy_pct']}% | Left: {ops['remaining_to_sell']} | BAR Rec: ${plan['recommended_bar']}\n"
        f"Note: {message or ops.get('notes') or 'Shift inventory update logged.'}"
    )
    tg_cfg = dict(cfg)
    custom_chat = (plan["rules"].get("telegram_chat_id") or "").strip()
    if custom_chat:
        tg_block = dict(cfg.get("telegram") or {})
        tg_block["chat_id"] = custom_chat
        tg_cfg["telegram"] = tg_block
    sent = send_telegram(tg_cfg, body)
    return {
        "ok": True,
        "telegram_sent": sent,
        "status": "sent_live" if sent else "preview_configure_telegram_bot_token",
        "message_preview": body,
    }


def list_competitor_inquiries(conn, requester_hotel_id: int, limit: int = 25) -> list:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM competitor_inquiries WHERE requester_hotel_id=? ORDER BY created_at DESC LIMIT ?",
            (requester_hotel_id, limit),
        )
    ]


def create_competitor_inquiry(conn, requester_hotel_id: int, payload: dict) -> dict:
    my_h = conn.execute("SELECT id, name, area FROM hotels WHERE id=?", (requester_hotel_id,)).fetchone()
    my_name = my_h["name"] if my_h else f"Hotel #{requester_hotel_id}"
    area = (my_h["area"] if my_h and my_h["area"] else "Miami Beach")

    target_id = payload.get("target_hotel_id")
    target_name = (payload.get("target_hotel_name") or "").strip()
    target_email = (payload.get("target_email") or "").strip()

    if target_id:
        th = conn.execute("SELECT id, name FROM hotels WHERE id=?", (int(target_id),)).fetchone()
        if th:
            target_name = target_name or th["name"]
            if not target_email:
                em = conn.execute(
                    "SELECT value FROM contacts WHERE hotel_id=? AND kind='email' ORDER BY confidence DESC LIMIT 1",
                    (int(target_id),),
                ).fetchone()
                if em:
                    target_email = em["value"]

    target_name = target_name or "Local Competitor Hotel"
    inq_type = payload.get("inquiry_type") or "courtesy_rate_swap"
    tpl = INQUIRY_TEMPLATES.get(inq_type) or INQUIRY_TEMPLATES["courtesy_rate_swap"]
    checkin = payload.get("checkin") or (date.today() + timedelta(days=1)).isoformat()
    rooms_req = max(1, int(payload.get("rooms_requested") or 1))

    subject = payload.get("subject") or tpl["subject"].format(
        target_name=target_name, my_name=my_name, area=area, checkin=checkin, rooms=rooms_req
    )
    body = payload.get("body") or tpl["body_tpl"].format(
        target_name=target_name, my_name=my_name, area=area, checkin=checkin, rooms=rooms_req
    )
    quoted_rate = payload.get("quoted_rate")
    quoted_val = float(quoted_rate) if quoted_rate not in (None, "") else None
    status = "replied_logged" if quoted_val is not None else (payload.get("status") or "drafted_ready_to_send")
    now = time.time()

    cur = conn.execute(
        """INSERT INTO competitor_inquiries
           (requester_hotel_id, target_hotel_id, target_hotel_name, target_email, inquiry_type,
            checkin, rooms_requested, subject, body, quoted_rate, status, created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            requester_hotel_id, int(target_id) if target_id else None, target_name, target_email,
            inq_type, checkin, rooms_req, subject, body, quoted_val, status, now,
        ),
    )
    conn.commit()
    return {
        "ok": True,
        "id": cur.lastrowid,
        "target_hotel_name": target_name,
        "target_email": target_email,
        "subject": subject,
        "body": body,
        "status": status,
        "inquiries": list_competitor_inquiries(conn, requester_hotel_id),
    }


ROOM_EQUIVALENCY_TIERS = {
    "standard_king": {
        "id": "standard_king",
        "label": "Standard King / Queen (Entry BAR)",
        "match_rule": "Standard King vs. Competitor Standard King/Queen",
        "mult": 1.00,
        "max_occ": 2,
        "rollaway_supported": False,
        "rollaway_note": "No rollaway (fire code max 2)",
    },
    "double_double": {
        "id": "double_double",
        "label": "Two Doubles / Two Queens (DD / QQ)",
        "match_rule": "Double-Double vs. Competitor Double-Double / Two Queens",
        "mult": 1.14,
        "max_occ": 4,
        "rollaway_supported": True,
        "rollaway_note": "Rollaway optional (+$35/nt)",
    },
    "suite_vs_suite": {
        "id": "suite_vs_suite",
        "label": "Junior / 1-Bedroom Suite (Suite vs. Suite)",
        "match_rule": "Suite vs. Competitor Equivalent Suite ONLY",
        "mult": 1.48,
        "max_occ": 4,
        "rollaway_supported": True,
        "rollaway_note": "Sofabed + Rollaway available (+$40/nt)",
    },
    "ocean_balcony": {
        "id": "ocean_balcony",
        "label": "Oceanview / Balcony Corner Upgrade",
        "match_rule": "Ocean/Balcony vs. Competitor Ocean/Balcony Category",
        "mult": 1.32,
        "max_occ": 3,
        "rollaway_supported": True,
        "rollaway_note": "Rollaway allowed (+$35/nt)",
    },
}

NIGHT_AUDIT_WINDOWS = [
    {
        "id": "pre_audit",
        "badge": "RECOMMENDED #1 · BEFORE AUDIT",
        "window": "11:30 PM – 1:15 AM (Pre-Night Audit)",
        "best_for": "Live tonight walk-in BAR, true rooms left before PMS date-roll, and same-night overflow swaps.",
        "why": "Front desk / Night Audit has low lobby traffic and tonight's remaining rooms & no-show exposure are still live before the 2:00 AM batch close.",
        "script": (
            "Hi! This is the Night Audit desk at {my_name} down the street. Before we roll our audit, "
            "we are checking local walk-in availability in case we need to refer overflow guests tonight. "
            "Do you still have rooms left tonight, what is your walk-in BAR (King / Double / Suite), "
            "and do you charge a resort fee or offer rollaway beds?"
        ),
    },
    {
        "id": "post_audit",
        "badge": "RECOMMENDED #2 · AFTER AUDIT",
        "window": "3:30 AM – 4:45 AM (Post-Night Audit)",
        "best_for": "Clean final actual occupancy %, final ADR, and tomorrow's 6:00 AM Morning Huddle Brief.",
        "why": "The PMS business date has rolled, credit-card batches are settled, and the auditor knows final sellout status and tomorrow's arrivals/departures.",
        "script": (
            "Good morning! Night Audit calling from {my_name} — now that the audit is wrapped up, "
            "mind swapping final occupancy % and tomorrow's opening BAR for our 6:00 AM morning huddle?"
        ),
    },
    {
        "id": "avoid_roll",
        "badge": "DO NOT CALL WINDOW",
        "window": "1:45 AM – 3:15 AM (Active Audit Roll)",
        "best_for": "Never disturb competing auditors during active PMS posting & credit card batch close.",
        "why": "Calling during batch roll gets quick hang-ups and harms neighbor courtesy relationships.",
        "script": "Wait until 3:30 AM (Post-Audit) or send a silent 1-Click Courtesy Email instead.",
    },
]


def _default_corridor_inclusions(area: str, stars: float) -> dict:
    """Typical corridor operational profile (editable per hotel in Room Ops)."""
    a = (area or "").lower()
    st = float(stars or 3.5)
    if "mimo" in a or "biscayne" in a:
        resort_fee = 0 if st <= 3.5 else 15
        tax_pct = 13
        hk_cadence = "Daily Stayover HK" if st >= 3.8 else "Every 3rd Day / On Request"
        rollaway_fee = 25
    elif "north beach" in a:
        resort_fee = 18 if st <= 3.4 else 28
        tax_pct = 14
        hk_cadence = "Daily Stayover HK" if st >= 3.6 else "Every 2nd Day HK"
        rollaway_fee = 35
    elif "mid-beach" in a:
        resort_fee = 35 if st < 4.2 else 42
        tax_pct = 14
        hk_cadence = "Daily Full HK + Turndown" if st >= 4.3 else "Daily Full HK"
        rollaway_fee = 45
    else:
        resort_fee = 29 if st <= 3.6 else 39
        tax_pct = 14
        hk_cadence = "Daily Full HK" if st >= 3.8 else "On-Request Stayover HK"
        rollaway_fee = 35
    return {
        "resort_fee": resort_fee,
        "tax_pct": tax_pct,
        "hk_cadence": hk_cadence,
        "rollaway_fee": rollaway_fee,
    }


def build_room_equivalency_matrix(
    conn,
    hotel_id: int,
    room_tier: str = "suite_vs_suite",
    occupancy: str = "double",
    include_rollaway: bool = False,
    comp_hotel_ids: list = None,
) -> dict:
    """Build an Apples-to-Apples Room-Type & Inclusions comparison table (Suite vs Suite,
    Double vs Double, Single vs Single, Rollaway bed fee, Resort fee, Housekeeping cadence,
    and True Out-the-Door normalized comp rate) using ONLY real scraped base rates."""
    tier_cfg = ROOM_EQUIVALENCY_TIERS.get(room_tier) or ROOM_EQUIVALENCY_TIERS["suite_vs_suite"]
    occ_key = occupancy if occupancy in ("single", "double", "triple_quad") else "double"
    extra_adult_fee = 0 if occ_key in ("single", "double") else 30

    ids_filter = list(dict.fromkeys([int(hotel_id)] + [int(x) for x in (comp_hotel_ids or []) if str(x).isdigit()]))
    if len(ids_filter) <= 1:
        my_h = conn.execute("SELECT area FROM hotels WHERE id=?", (hotel_id,)).fetchone()
        area = (my_h["area"] if my_h and my_h["area"] else "South Beach")
        neighbors = conn.execute(
            "SELECT id FROM hotels WHERE id != ? ORDER BY CASE WHEN area=? THEN 0 ELSE 1 END, id LIMIT 8",
            (hotel_id, area),
        ).fetchall()
        ids_filter = [int(hotel_id)] + [int(r["id"]) for r in neighbors]

    placeholders = ",".join("?" for _ in ids_filter)
    rows = conn.execute(
        f"""SELECT h.id, h.name, h.area, h.stars, h.est_rooms, h.booking_engine,
                   r.nightly_price, r.parity_status, r.undercut_pct
            FROM hotels h
            LEFT JOIN (
              SELECT hotel_id, nightly_price, parity_status, undercut_pct, MAX(scraped_at)
              FROM rates GROUP BY hotel_id
            ) r ON r.hotel_id = h.id
            WHERE h.id IN ({placeholders})""",
        tuple(ids_filter),
    ).fetchall()

    by_id = {int(r["id"]): dict(r) for r in rows}
    ordered = [by_id[i] for i in ids_filter if i in by_id]

    items = []
    my_otd = None
    for idx, h in enumerate(ordered):
        base_bar = h.get("nightly_price")
        if base_bar is None:
            continue
        base_bar = float(base_bar)
        inc = _default_corridor_inclusions(h.get("area") or "", h.get("stars") or 3.5)
        cat_bar = round(base_bar * tier_cfg["mult"] + extra_adult_fee)
        roll_fee = inc["rollaway_fee"] if (include_rollaway and tier_cfg["rollaway_supported"]) else 0
        subtotal = cat_bar + inc["resort_fee"] + roll_fee
        tax_amt = round(subtotal * (inc["tax_pct"] / 100.0))
        true_otd = round(subtotal + tax_amt)
        is_primary = (int(h["id"]) == int(hotel_id))
        if is_primary:
            my_otd = true_otd
        items.append({
            "hotel_id": int(h["id"]),
            "name": h["name"],
            "area": h.get("area") or "Miami Beach",
            "stars": h.get("stars") or 3.5,
            "is_primary": is_primary,
            "scraped_base_bar": round(base_bar),
            "matched_category": tier_cfg["label"],
            "occupancy": occ_key,
            "category_bar": cat_bar,
            "resort_fee": inc["resort_fee"],
            "rollaway_allowed": tier_cfg["rollaway_supported"],
            "rollaway_fee": roll_fee,
            "hk_cadence": inc["hk_cadence"],
            "tax_pct": inc["tax_pct"],
            "true_otd_total": true_otd,
            "parity_status": h.get("parity_status") or "PARITY",
        })

    for it in items:
        it["spread_vs_my_otd"] = round(it["true_otd_total"] - my_otd) if my_otd is not None else 0

    comp_otds = [it["true_otd_total"] for it in items if not it["is_primary"]]
    comp_avg_otd = round(sum(comp_otds) / len(comp_otds)) if comp_otds else (my_otd or 0)

    return {
        "ok": True,
        "room_tier": tier_cfg,
        "occupancy": occ_key,
        "include_rollaway": bool(include_rollaway),
        "my_true_otd": my_otd,
        "comp_avg_otd": comp_avg_otd,
        "otd_advantage": round(comp_avg_otd - (my_otd or 0)),
        "items": items,
        "available_tiers": list(ROOM_EQUIVALENCY_TIERS.values()),
        "night_audit_windows": NIGHT_AUDIT_WINDOWS,
    }
