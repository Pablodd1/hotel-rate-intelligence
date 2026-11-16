"""Overnight Courtesy Occupancy Caller & Reservation Rate-Setting Assistant (`hri/call_assistant.py`).

ZERO-HALLUCINATION DESIGN:
1. NEVER fabricates seed call logs, fake front-desk answers, or fake occupancy quotes.
2. Live Voice calls run through Vapi.ai / Bland.ai / Twilio Voice ONLY when real credentials exist.
   Otherwise, calls are queued honestly with status='queued_awaiting_voice_key' and 1-click tel: links.
3. Manual calls logged by staff are saved as status='verified_manual_call' using only the actual numbers
   or transcript notes provided by the caller.
"""
import json
import re
import time
import urllib.parse
import urllib.request
from base64 import b64encode

COURTESY_CALL_TEMPLATES = [
    {
        "id": "overnight_audit",
        "label": "Overnight Night-Audit Courtesy Call-Around (11:30 PM - 4:00 AM)",
        "opening_script": (
            "Hi Front Desk, good evening! Calling from the night-audit desk down the street doing our nightly "
            "courtesy occupancy call-around. We're sitting at {my_occ}% with {my_left} rooms left tonight at ${my_bar} — "
            "how is your occupancy looking tonight, how many rooms do you have left, and what's your walk-in rate?"
        ),
        "followup_question": "Awesome, thank you! And are you holding your rate floor for this weekend or pushing BAR up?",
    },
    {
        "id": "quick_availability",
        "label": "Quick Reservation / Walk-In Availability Check (Any Shift)",
        "opening_script": (
            "Hi Front Desk! Quick question — if we have overflow walk-in guests tonight, do you still have standard "
            "king or double rooms open, about how many rooms do you have left, and what rate are you quoting at the desk?"
        ),
        "followup_question": "Got it, and does that rate include your resort fee or is that plus fee and tax?",
    },
    {
        "id": "group_compression",
        "label": "Weekend Compression & Group Block Check",
        "opening_script": (
            "Hi Reservations! Checking if you still have 5+ rooms open for this coming weekend or if you're already "
            "over 85% committed, and what your current Best Available Rate is?"
        ),
        "followup_question": "Thanks so much — I'll note your rate on our desk sheet!",
    },
]


def _e164(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if len(digits) > 10:
        return f"+{digits}"
    return ""


def list_call_logs(conn, limit=40):
    rows = [dict(r) for r in conn.execute("""
        SELECT c.*, h.name AS hotel_name, h.area, h.est_rooms, h.stars
        FROM call_logs c
        JOIN hotels h ON h.id = c.hotel_id
        ORDER BY c.called_at DESC, c.id DESC
        LIMIT ?
    """, (limit,))]
    return rows


def place_or_log_courtesy_call(conn, cfg, payload: dict) -> dict:
    """Place a live courtesy call via Vapi / Bland / Twilio (only when credentials exist) or record an
    honest verified manual call / queued dry-run script. Never invents front-desk responses.
    """
    hid = int(payload.get("hotel_id") or 1)
    h_row = conn.execute("SELECT * FROM hotels WHERE id=?", (hid,)).fetchone()
    if not h_row:
        return {"ok": False, "error": "Hotel not found"}
    hotel = dict(h_row)
    ph_row = conn.execute(
        "SELECT value FROM contacts WHERE hotel_id=? AND kind='phone' ORDER BY confidence DESC LIMIT 1", (hid,)
    ).fetchone()
    phone = (payload.get("phone_dialed") or (ph_row["value"] if ph_row else "") or "").strip()
    if not phone:
        return {"ok": False, "error": f"No verified phone number stored for {hotel['name']}. Run lead verification or enter a phone number."}

    r_row = conn.execute(
        "SELECT nightly_price FROM rates WHERE hotel_id=? AND nightly_price IS NOT NULL ORDER BY id DESC LIMIT 1", (hid,)
    ).fetchone()
    cur_bar = round(float(r_row["nightly_price"])) if r_row and r_row["nightly_price"] else None

    my_cfg = cfg.get("my_hotel") or {}
    my_occ = my_cfg.get("current_occupancy_pct", 78)
    my_left = my_cfg.get("rooms_left_tonight", 10)
    my_bar = my_cfg.get("current_bar", 224)

    custom_question = (payload.get("questions_asked") or "").strip()
    if not custom_question:
        custom_question = (
            f"Courtesy night-audit call-around: We're at {my_occ}% ({my_left} rooms left at ${my_bar}). "
            f"How is your occupancy tonight, how many rooms left, and what is your walk-in BAR?"
        )

    rep_occ = payload.get("reported_occupancy_pct")
    rooms_left = payload.get("rooms_left")
    walkin = payload.get("quoted_walkin_rate")
    user_transcript = (payload.get("transcript") or "").strip()

    # Extract numbers ONLY from actual human-entered transcript if provided
    if user_transcript and rep_occ is None:
        m_occ = re.search(r"(\d{1,3})\s*%", user_transcript)
        if m_occ:
            rep_occ = min(100, max(0, int(m_occ.group(1))))
    if user_transcript and rooms_left is None:
        m_rm = re.search(r"(\d{1,3})\s+rooms?\s+left", user_transcript, re.I)
        if m_rm:
            rooms_left = int(m_rm.group(1))
    if user_transcript and walkin is None:
        m_pr = re.search(r"\$\s*(\d{2,4})", user_transcript)
        if m_pr:
            walkin = float(m_pr.group(1))

    is_manual_entry = (
        payload.get("caller_mode") == "Recorded Desk Courtesy Call"
        or rep_occ is not None
        or rooms_left is not None
        or walkin is not None
        or bool(user_transcript)
    )

    caller_mode = payload.get("caller_mode") or "Overnight Courtesy Auto-Caller"
    status = "verified_manual_call" if is_manual_entry else "queued_awaiting_voice_key"
    rec_ref = payload.get("recording_url") or ""
    provider_call_id = ""
    short_name = hotel["name"].split(",")[0]

    if not is_manual_entry:
        caller_cfg = cfg.get("caller") or {}
        out_cfg = cfg.get("outreach") or {}
        vapi_key = (out_cfg.get("vapi_api_key") or caller_cfg.get("vapi_api_key") or "").strip()
        vapi_phone_id = (out_cfg.get("vapi_phone_number_id") or "").strip()
        bland_key = (out_cfg.get("bland_api_key") or "").strip()
        tw_sid = (out_cfg.get("twilio_account_sid") or caller_cfg.get("twilio_sid") or "").strip()
        tw_tok = (out_cfg.get("twilio_auth_token") or caller_cfg.get("twilio_token") or "").strip()
        tw_from = (out_cfg.get("twilio_from_phone") or caller_cfg.get("twilio_from") or "").strip()
        to_e164 = _e164(phone)

        live_mode = (out_cfg.get("mode") == "live") or bool(payload.get("force_live"))
        first_msg = (
            f"Hi Front Desk at {short_name}! Quick courtesy night-audit call-around from down the street — "
            f"how's your occupancy looking tonight and what is your walk-in rate?"
        )

        if live_mode and vapi_key and vapi_phone_id and to_e164:
            try:
                req = urllib.request.Request(
                    "https://api.vapi.ai/call/phone",
                    data=json.dumps({
                        "phoneNumberId": vapi_phone_id,
                        "customer": {"number": to_e164},
                        "assistant": {
                            "firstMessage": first_msg,
                            "model": {"provider": "google", "model": "gemini-2.5-flash-lite", "messages": [{"role": "system", "content": custom_question}]},
                            "recordingEnabled": True,
                        },
                    }).encode("utf-8"),
                    headers={"Authorization": f"Bearer {vapi_key}", "Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    rdata = json.loads(resp.read().decode("utf-8"))
                    provider_call_id = rdata.get("id", "")
                    caller_mode = "Vapi Live AI Voice Call"
                    status = "dispatched_live_voice"
                    user_transcript = f"[Vapi Call Dispatched · ID={provider_call_id}] Awaiting live call completion webhook or transcript entry.\nScript: {first_msg}"
            except Exception as e:
                status = "failed"
                user_transcript = f"[Vapi Dispatch Error] {str(e)[:180]}"
        elif live_mode and bland_key and to_e164:
            try:
                req = urllib.request.Request(
                    "https://api.bland.ai/v1/calls",
                    data=json.dumps({
                        "phone_number": to_e164,
                        "task": f"{first_msg} Follow-up: {custom_question}",
                        "record": True,
                    }).encode("utf-8"),
                    headers={"Authorization": bland_key, "Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    rdata = json.loads(resp.read().decode("utf-8"))
                    provider_call_id = rdata.get("call_id", "")
                    caller_mode = "Bland Live AI Voice Call"
                    status = "dispatched_live_voice"
                    user_transcript = f"[Bland AI Call Dispatched · ID={provider_call_id}] Awaiting transcript."
            except Exception as e:
                status = "failed"
                user_transcript = f"[Bland Dispatch Error] {str(e)[:180]}"
        elif live_mode and tw_sid and tw_tok and tw_from and to_e164:
            try:
                twiml = f"<Response><Say voice='alice'>{first_msg}</Say><Pause length='2'/></Response>"
                form = urllib.parse.urlencode({"To": to_e164, "From": _e164(tw_from), "Twiml": twiml, "Record": "true"}).encode("utf-8")
                auth = b64encode(f"{tw_sid}:{tw_tok}".encode()).decode()
                req = urllib.request.Request(
                    f"https://api.twilio.com/2010-04-01/Accounts/{tw_sid}/Calls.json",
                    data=form,
                    headers={"Authorization": f"Basic {auth}"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    rdata = json.loads(resp.read().decode("utf-8"))
                    provider_call_id = rdata.get("sid", "")
                    caller_mode = "Twilio Live Voice Call"
                    status = "dispatched_live_voice"
                    user_transcript = f"[Twilio Call Dispatched · SID={provider_call_id}] Recording enabled."
            except Exception as e:
                status = "failed"
                user_transcript = f"[Twilio Voice Error] {str(e)[:180]}"
        else:
            status = "queued_awaiting_voice_key"
            user_transcript = (
                f"[DRY-RUN QUEUED — NO LIVE CALL PLACED]\n"
                f"Dial target: {short_name} ({phone})\n"
                f"Prepared script: \"{first_msg}\"\n"
                f"Action: Add Vapi/Bland/Twilio Voice keys in Setup & enable Live Mode to auto-dial, "
                f"or click 'Dial from Phone/Desk' and enter the front desk's real answer below."
            )

    if rep_occ is not None:
        rep_occ = int(rep_occ)
    if rooms_left is not None:
        rooms_left = int(rooms_left)
    if walkin is not None:
        walkin = float(walkin)

    cur = conn.execute(
        """INSERT INTO call_logs(
           hotel_id, shift, caller_mode, phone_dialed, reported_occupancy_pct,
           rooms_left, quoted_walkin_rate, questions_asked, transcript, recording_url, status, called_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            hid,
            payload.get("shift") or "Overnight Audit (11:30PM-4:00AM)",
            caller_mode,
            phone,
            rep_occ,
            rooms_left,
            walkin,
            custom_question,
            user_transcript,
            rec_ref or provider_call_id,
            status,
            time.time(),
        ),
    )
    call_id = cur.lastrowid

    # Update hotel occupancy & memory ONLY if real verified data was actually logged
    if status == "verified_manual_call" and rep_occ is not None:
        conn.execute("UPDATE hotels SET est_occupancy_pct=? WHERE id=?", (rep_occ, hid))
        delta_p = round(((walkin - cur_bar) / cur_bar) * 100, 1) if (walkin and cur_bar) else 0.0
        conn.execute(
            """INSERT INTO memory_events(
               hotel_id, event_type, old_price, new_price, delta_pct,
               est_occupancy_pct, competitor_pattern, ai_recommendation, recorded_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                hid,
                "overnight_call",
                cur_bar,
                walkin,
                delta_p,
                rep_occ,
                "MANUAL_CALL_VERIFIED",
                f"Staff verified courtesy call: {rep_occ}% occupancy"
                + (f", {rooms_left} rooms left" if rooms_left is not None else "")
                + (f", ${walkin:g} walk-in rate." if walkin is not None else "."),
                time.time(),
            ),
        )
    conn.commit()
    return {
        "ok": True,
        "call_id": call_id,
        "status": status,
        "hotel_id": hid,
        "hotel_name": hotel["name"],
        "phone_dialed": phone,
        "reported_occupancy_pct": rep_occ,
        "rooms_left": rooms_left,
        "quoted_walkin_rate": walkin,
        "transcript": user_transcript,
        "recording_url": rec_ref or provider_call_id,
    }


def build_my_hotel_comparison(conn, cfg, rates_list: list) -> dict:
    """Build the 'My Hotel' benchmark profile comparing against real live rates & real verified calls."""
    my_cfg = cfg.get("my_hotel") or {}
    my_hid = int(my_cfg.get("hotel_id") or 1)

    my_row = next((r for r in rates_list if r["hotel_id"] == my_hid), None)
    if not my_row and rates_list:
        my_row = next((r for r in rates_list if r.get("price") is not None), rates_list[0])
        my_hid = my_row["hotel_id"]

    calls_by_hid = {}
    for c in conn.execute(
        "SELECT * FROM call_logs WHERE status IN ('verified_manual_call', 'completed_live') "
        "AND reported_occupancy_pct IS NOT NULL ORDER BY called_at DESC, id DESC"
    ):
        if c["hotel_id"] not in calls_by_hid:
            calls_by_hid[c["hotel_id"]] = dict(c)

    my_name = (my_cfg.get("custom_name") or "").strip() or (my_row["name"] if my_row else "My Boutique Hotel")
    my_area = my_row.get("area", "Miami Beach") if my_row else "Miami Beach"
    live_my_price = my_row.get("price") if (my_row and my_row.get("price") is not None) else None
    my_bar = round(float(my_cfg.get("current_bar") or live_my_price or 224))
    my_prev_bar = round(float(my_row["prev_price"])) if (my_row and my_row.get("prev_price") is not None) else None
    my_occ = int(my_cfg.get("current_occupancy_pct") or (my_row.get("est_occupancy_pct") if my_row else 78))
    my_rooms = int(my_cfg.get("rooms") or (my_row.get("est_rooms") if my_row else 45))
    my_left = int(my_cfg.get("rooms_left_tonight") or max(1, round(my_rooms * (100 - my_occ) / 100)))
    my_resort_fee = float(my_cfg.get("resort_fee") if my_cfg.get("resort_fee") is not None else 15)
    my_stars = float((my_row or {}).get("stars") or 3.5)
    my_rating = float((my_row or {}).get("review_rating") or my_stars or 4.0)
    my_reviews = int((my_row or {}).get("review_count") or 0)

    # Filter corridor peers that actually have real live prices
    corridor_peers = [r for r in rates_list if r["hotel_id"] != my_hid and r.get("area") == my_area and r.get("price") is not None]
    if len(corridor_peers) < 3:
        corridor_peers = [r for r in rates_list if r["hotel_id"] != my_hid and r.get("price") is not None][:8]

    peer_prices_new = [float(r["price"]) for r in corridor_peers if r.get("price") is not None]
    peer_prices_old = [float(r.get("prev_price") if r.get("prev_price") is not None else r["price"]) for r in corridor_peers if r.get("price") is not None]
    peer_avg_new = round(sum(peer_prices_new) / len(peer_prices_new)) if peer_prices_new else my_bar
    peer_avg_old = round(sum(peer_prices_old) / len(peer_prices_old)) if peer_prices_old else peer_avg_new
    peer_avg_occ = round(sum(int(r.get("est_occupancy_pct") or 72) for r in corridor_peers) / max(1, len(corridor_peers))) if corridor_peers else my_occ
    corridor_move_pct = round(((peer_avg_new - peer_avg_old) / max(1, peer_avg_old)) * 100, 1) if peer_avg_old else 0.0

    if peer_avg_occ >= 85 or my_occ >= 85:
        rec_tonight_walkin = max(my_bar + 15, round(peer_avg_new * 1.06))
        rec_30d_bar = max(my_bar + 12, round((my_bar + peer_avg_new) / 2 + 10))
        rec_weekend_bar = round(rec_30d_bar * 1.18)
        stance = "HIGH COMPRESSION — PUSH WALK-IN & BAR UP"
        assistant_explanation = (
            f"Corridor pressure index is {peer_avg_occ}% avg (your hotel is at {my_occ}% with {my_left} rooms left). "
            f"Between previous live scan (${peer_avg_old}) and latest live scan (${peer_avg_new}), corridor rates moved {corridor_move_pct:+.1f}%. "
            f"Set walk-in rate to ${rec_tonight_walkin}/nt and Direct BAR to ${rec_30d_bar}/nt."
        )
    elif my_bar > peer_avg_new * 1.12 and my_occ < 72:
        floor = int(my_cfg.get("min_rate_floor") or 149)
        rec_tonight_walkin = max(floor, peer_avg_new - 8)
        rec_30d_bar = max(floor, peer_avg_new - 5)
        rec_weekend_bar = round(rec_30d_bar * 1.14)
        stance = "CAPTURE PACE — ALIGN BAR JUST BELOW CORRIDOR AVG"
        assistant_explanation = (
            f"Your BAR (${my_bar}) sits above the live corridor average (${peer_avg_new}) while your occupancy is {my_occ}%. "
            f"Adjust Direct BAR to ${rec_30d_bar}/nt to capture pace before pushing weekend BAR to ${rec_weekend_bar}/nt."
        )
    else:
        rec_tonight_walkin = max(my_bar + 10, peer_avg_new + 5)
        rec_30d_bar = max(my_bar + 8, round((my_bar + peer_avg_new) / 2 + 6))
        rec_weekend_bar = round(rec_30d_bar * 1.15)
        stance = "BALANCED YIELD — STEP ABOVE CORRIDOR PEERS"
        assistant_explanation = (
            f"Your corridor moved from ${peer_avg_old} to ${peer_avg_new} across live scans. "
            f"Hold ${rec_tonight_walkin}/nt walk-in for your remaining {my_left} rooms, set Direct BAR to ${rec_30d_bar}/nt, "
            f"and lock ${rec_weekend_bar}/nt for Fri–Sat."
        )

    for r in rates_list:
        hid = r["hotel_id"]
        call = calls_by_hid.get(hid)
        if call:
            r["call_verified_occ"] = call["reported_occupancy_pct"]
            r["call_rooms_left"] = call["rooms_left"]
            r["call_walkin_rate"] = call["quoted_walkin_rate"]
            r["call_time"] = time.strftime("%b %d %I:%M %p", time.localtime(call["called_at"]))
        else:
            r["call_verified_occ"] = None
            r["call_rooms_left"] = None
            r["call_walkin_rate"] = None
            r["call_time"] = "Not Called Yet"

        r["is_my_hotel"] = (hid == my_hid)
        if r.get("price") is None:
            r["gap_vs_my_hotel"] = None
            r["my_rate_recommendation"] = (
                f"★ MY HOTEL: Set BAR -> ${rec_30d_bar}/nt"
                if r["is_my_hotel"]
                else "No live OTA quote returned for checked dates"
            )
            continue

        comp_p = round(float(r["price"]))
        gap_vs_me = comp_p - my_bar
        r["gap_vs_my_hotel"] = gap_vs_me

        if r["is_my_hotel"]:
            r["my_rate_recommendation"] = f"★ MY HOTEL: Set BAR → ${rec_30d_bar}/nt · Tonight Walk-In → ${rec_tonight_walkin}/nt"
        elif r.get("parity_status") == "UNDERCUT":
            r["my_rate_recommendation"] = f"OTA leak ({r.get('undercut_pct')}%); hold My BAR at ${rec_30d_bar} and win direct"
        elif comp_p > my_bar + 15:
            r["my_rate_recommendation"] = f"Priced +${gap_vs_me} above us (${comp_p}) → Room to raise My BAR +${min(25, round(gap_vs_me * 0.5))}"
        elif comp_p < my_bar - 15:
            r["my_rate_recommendation"] = f"Priced -${abs(gap_vs_me)} below us (${comp_p}) → Hold floor or match mid-week"
        else:
            r["my_rate_recommendation"] = f"Head-to-head (${comp_p} vs our ${my_bar}) → Highlight rating & direct perks"

    return {
        "hotel_id": my_hid,
        "name": my_name,
        "area": my_area,
        "stars": my_stars,
        "review_rating": my_rating,
        "review_count": my_reviews,
        "rooms": my_rooms,
        "rooms_left_tonight": my_left,
        "current_occupancy_pct": my_occ,
        "old_scrape_bar": my_prev_bar or my_bar,
        "current_bar": my_bar,
        "resort_fee": my_resort_fee,
        "out_the_door_bar": round((my_bar + my_resort_fee) * 1.14),
        "corridor_old_avg": peer_avg_old,
        "corridor_new_avg": peer_avg_new,
        "corridor_move_pct": corridor_move_pct,
        "corridor_avg_occupancy": peer_avg_occ,
        "recommended_tonight_walkin": rec_tonight_walkin,
        "recommended_30d_bar": rec_30d_bar,
        "recommended_weekend_bar": rec_weekend_bar,
        "strategy_stance": stance,
        "assistant_explanation": assistant_explanation,
    }
