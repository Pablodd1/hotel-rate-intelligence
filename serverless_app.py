"""Single Vercel WSGI entrypoint for the HRI dashboard API.

Declared in pyproject.toml ([tool.vercel] entrypoint). Receives every
non-static request with the REAL path — no rewrite path-collapsing.
"""
import json
import os
from urllib.parse import parse_qs

_HERE = os.path.dirname(os.path.abspath(__file__))
_API_DIR = os.path.join(_HERE, "api")
_DASH_PATH = os.path.join(_HERE, "dashboard", "index.html")
_WEBSITE_PATH = os.path.join(_HERE, "dashboard", "website.html")
_PORTAL_PATH = os.path.join(_HERE, "dashboard", "client_portal.html")
_MC_PATH = os.path.join(_HERE, "dashboard", "mission_control.html")
_KEY = os.environ.get("HRI_AUTH_KEY", "hri-miami-2026")
_dash_cache = None


def _dashboard(target_path=None):
    p = target_path or _DASH_PATH
    if not os.path.exists(p):
        p = _DASH_PATH
    with open(p, encoding="utf-8") as f:
        return f.read().encode("utf-8")


def _load(name):
    with open(os.path.join(_API_DIR, name), encoding="utf-8") as f:
        return f.read().encode("utf-8")


def _reply(start_response, status, body, ctype="application/json; charset=utf-8"):
    headers = [("Content-Type", ctype), ("Cache-Control", "no-store")]
    if isinstance(body, str):
        body = body.encode("utf-8")
    headers.append(("Content-Length", str(len(body))))
    start_response(status, headers)
    return [body]


def _read_body(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        raw = environ["wsgi.input"].read(length) if length > 0 else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return {}


def _load_asset(rel_name):
    fp = os.path.join(_HERE, "dashboard", "assets", os.path.basename(rel_name))
    with open(fp, "rb") as f:
        return f.read()


def _notify_owner_resend(subject, body_text, skip=False):
    if skip:
        return False
    rkey = (os.environ.get("RESEND_API_KEY") or "").strip()
    if not rkey:
        return False
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps({
                "from": "HotelRateIntel Alerts <jasmel@hotelrateintel.com>",
                "to": ["jasmelacosta@gmail.com"],
                "reply_to": ["jasmelacosta@gmail.com"],
                "subject": subject,
                "text": body_text,
            }).encode("utf-8"),
            headers={"Authorization": f"Bearer {rkey}", "Content-Type": "application/json", "User-Agent": "HotelRateIntel/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def app(environ, start_response):
    raw = environ.get("RAW_URI") or environ.get("REQUEST_URI") or environ.get("PATH_INFO", "/")
    path = raw.split("?")[0]
    params = parse_qs(environ.get("QUERY_STRING", ""))
    if not params and "?" in raw:
        params = parse_qs(raw.split("?", 1)[1])
    key = (params.get("k") or [""])[0]

    # Public pages, assets, portal auth, public auditor/chat, and token-gated admin APIs
    # work directly on https://hotelrateintel.com without requiring ?k=.
    is_public_or_token_path = (
        not path.startswith("/api/")
        or path.startswith("/api/public/")
        or path.startswith("/api/accounts/register")
        or path.startswith("/api/client/")
        or path.startswith("/api/audit/")
        or path.startswith("/api/admin/")
    )
    if not is_public_or_token_path and (not key or key != _KEY):
        return _reply(start_response, "401 Unauthorized",
                      json.dumps({"error": "auth key required: ?k=<key>"}, indent=1))

    if not path.startswith("/api/"):
        if path.startswith("/assets/"):
            rel = os.path.basename(path)
            try:
                ctype = "image/jpeg" if rel.endswith(".jpg") else ("image/png" if rel.endswith(".png") else "application/octet-stream")
                return _reply(start_response, "200 OK", _load_asset(rel), ctype=ctype)
            except FileNotFoundError:
                return _reply(start_response, "404 Not Found", b"not found", ctype="text/plain")
        if path in ("/", "/website", "/website.html", "/landing"):
            return _reply(start_response, "200 OK", _dashboard(_WEBSITE_PATH), ctype="text/html; charset=utf-8")
        if path in ("/portal", "/client", "/client_portal.html"):
            return _reply(start_response, "200 OK", _dashboard(_PORTAL_PATH), ctype="text/html; charset=utf-8")
        if path in ("/mission-control", "/admin", "/dashboard", "/index.html"):
            return _reply(start_response, "200 OK", _dashboard(_MC_PATH), ctype="text/html; charset=utf-8")
        if path.startswith("/audit"):
            hid = (params.get("hotel_id") or ["4"])[0]
            pitches = json.loads(_load("snapshot_pitches.json"))
            pitch = pitches.get(str(hid)) or next(iter(pitches.values()))
            from hri.sales_engine import build_printable_audit_html
            return _reply(start_response, "200 OK", build_printable_audit_html(pitch), ctype="text/html; charset=utf-8")
        return _reply(start_response, "200 OK", _dashboard(), ctype="text/html; charset=utf-8")

    body = _read_body(environ) if environ.get("REQUEST_METHOD") == "POST" else {}

    if path.startswith("/api/public/landing"):
        mr = json.loads(_load("snapshot_market_research.json"))
        hotels = json.loads(_load("snapshot_hotels.json")).get("hotels") or []
        from hri.tenant_engine import TIER_CATALOG, COMPETITOR_COMPARISON_MATRIX
        sample_labels = {
            1: "Sample Demo #1 · North Beach All-Suites",
            2: "Sample Demo #2 · Boutique Beachfront",
            4: "Sample Demo #3 · South Beach Art Deco",
        }
        demo_samples = [
            {
                "id": h["id"],
                "name": sample_labels.get(int(h["id"]), "Sample Boutique Demo"),
                "area": h.get("area"),
                "price": h.get("price"),
                "parity_status": h.get("parity_status"),
                "demo_url": f"/portal?demo_hotel={h['id']}",
                "audit_url": f"/audit?hotel_id={h['id']}",
            }
            for h in hotels if int(h["id"]) in sample_labels
        ]
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "market_summary": mr.get("summary") or {},
            "corridors": mr.get("corridors") or [],
            "tiers": TIER_CATALOG,
            "comparison_matrix": COMPETITOR_COMPARISON_MATRIX,
            "owner_callback_phone": "",
            "hotels_directory": demo_samples,
        }))
    if path.startswith("/api/public/chat") and environ.get("REQUEST_METHOD") == "POST":
        msg = (body.get("message") or "").strip()
        pitches = json.loads(_load("snapshot_pitches.json"))
        matched = next((p for p in pitches.values() if msg and msg.lower() in (p.get("hotel", {}).get("name", "").lower())), None)
        if matched:
            h = matched["hotel"]
            ri = matched.get("rate_intel") or {}
            return _reply(start_response, "200 OK", json.dumps({
                "ok": True,
                "persona": "Marco · Miami Revenue Hawk (Aggressive Closer)",
                "hotel_id": h["id"],
                "reply": (
                    f"BOOM!! {h['name']} ({h.get('area')}) live benchmark: Direct BAR ${ri.get('direct_bar') or 'N/A'}/nt "
                    f"vs {ri.get('lowest_ota_name') or 'OTA'} ${ri.get('lowest_ota_price') or 'N/A'}/nt! "
                    f"Launch their isolated Demo Panel below or drop your phone # for an instant Miami callback!"
                ),
                "actions": [{"label": f"🚀 Open {h['name'][:18]} Demo", "type": "link", "url": f"/portal?demo_hotel={h['id']}"}],
                "owner_direct_phone": "",
            }))
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "persona": "Marco · Miami Revenue Hawk (Aggressive Closer)",
            "reply": "LET'S GO!! Live Miami rates for 49 boutique hotels are pre-loaded right here — open any hotel's Demo Panel or click Live Website Auditor to inspect OTA parity & ROI!",
            "actions": [{"label": "🚀 Launch Demo Client #1", "type": "link", "url": "/portal?demo=1"}],
            "owner_direct_phone": "",
        }))
    if path.startswith("/api/public/callback") and environ.get("REQUEST_METHOD") == "POST":
        ph = (body.get("phone") or "").strip()
        nm = (body.get("name") or "Hotel Lead").strip()
        hn = (body.get("hotel_name") or "Website Visitor").strip()
        if not ph:
            return _reply(start_response, "400 Bad Request", json.dumps({"ok": False, "error": "Enter a valid phone number."}))
        _notify_owner_resend(
            f"HOT WEBSITE CALLBACK: {hn} ({ph})",
            f"New callback request on hotelrateintel.com:\n\nHotel: {hn}\nName: {nm}\nPhone: {ph}\nHotel ID: {body.get('hotel_id') or ''}",
            skip=("555-0199" in ph or "5550199" in ph),
        )
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "phone_e164": ph,
            "status": "owner_notified",
            "message": f"Locked in! Your callback request for {hn} ({ph}) was sent straight to Jasmel in Miami.",
        }))
    if path.startswith("/api/accounts/register") and environ.get("REQUEST_METHOD") == "POST":
        em = (body.get("email") or "").strip()
        hn = (body.get("hotel_name") or "").strip()
        hid = str(body.get("hotel_id") or "").strip()
        if not hid.isdigit():
            all_hotels = json.loads(_load("snapshot_hotels.json")).get("hotels") or []
            m = next((h for h in all_hotels if hn and hn.lower() in h.get("name", "").lower()), None)
            hid = str(m["id"]) if m else "1"
        tier = (body.get("tier") or "free").strip().lower()
        uname = (body.get("username") or "").strip() or f"hotel{hid}"
        price_map = {"free": 0, "core_99": 99, "pro_199": 199, "portfolio_399": 399}
        _notify_owner_resend(
            f"NEW PORTAL SIGNUP ({tier.upper()}): {hn or ('Hotel #' + hid)}",
            f"A hotel just registered on hotelrateintel.com!\n\nHotel: {hn or ('Hotel #' + hid)}\nEmail: {em}\nUsername: {uname}\nPlan Tier: {tier}\nDemo Link: https://hotelrateintel.com/portal?demo_hotel={hid}",
            skip=("smoke@" in em.lower()),
        )
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "token": f"demo-hotel-{hid}",
            "portal_url": f"/portal?demo_hotel={hid}",
            "account": {"id": int(hid), "username": uname, "tier": tier, "monthly_price": price_map.get(tier, 0), "primary_hotel_id": int(hid)},
        }))
    if path.startswith("/api/client/login") and environ.get("REQUEST_METHOD") == "POST":
        dh = str(body.get("demo_hotel_id") or "").strip()
        if dh.isdigit():
            return _reply(start_response, "200 OK", json.dumps({
                "ok": True,
                "token": f"demo-hotel-{dh}",
                "account": {"id": int(dh), "username": f"demo_h{dh}", "primary_hotel_id": int(dh), "tier": "pro_199"},
            }))
        u = (body.get("username") or "avalon").strip().lower()
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "token": "demo-hotel-1" if (body.get("demo") or u == "avalon") else f"demo-user-{u}",
            "account": {"id": 1, "username": u or "avalon", "primary_hotel_id": 1, "tier": "pro_199"},
        }))
    if path.startswith("/api/client/portal"):
        dh = (params.get("demo_hotel") or [""])[0].strip()
        tok = (environ.get("HTTP_X_CLIENT_TOKEN") or (params.get("token") or [""])[0]).strip()
        if not dh and tok.startswith("demo-hotel-"):
            dh = tok.replace("demo-hotel-", "")
        hid = int(dh) if dh.isdigit() else 1
        all_hotels = json.loads(_load("snapshot_hotels.json")).get("hotels") or []
        pitches = json.loads(_load("snapshot_pitches.json"))
        primary = next((h for h in all_hotels if int(h["id"]) == hid), all_hotels[0] if all_hotels else {})
        area = primary.get("area") or "South Beach"
        comp = [primary] + [h for h in all_hotels if int(h["id"]) != int(primary.get("id", 0)) and h.get("area") == area][:8]
        for idx, h in enumerate(comp):
            h["is_primary"] = (idx == 0)
            h["tags"] = []
        from hri.sales_engine import build_comp_set_svg, build_ota_ladder_svg, MIAMI_COMPRESSION_EVENTS
        from hri.tenant_engine import TIER_CATALOG, TIER_BY_ID
        ptier = (params.get("preview_tier") or ["pro_199"])[0]
        tier_meta = TIER_BY_ID.get(ptier, TIER_CATALOG[2])
        comp = comp[: 1 + int(tier_meta.get("max_competitors") or 8)]
        my_bar = float(primary.get("price") or 220)
        nb_prices = [float(x["price"]) for x in comp[1:] if x.get("price")]
        comp_avg = round(sum(nb_prices) / len(nb_prices)) if nb_prices else round(my_bar)
        pitch = pitches.get(str(hid)) or next(iter(pitches.values()), {})
        ri = pitch.get("rate_intel") or {}
        ota_svg = build_ota_ladder_svg(primary.get("name") or "Hotel", my_bar, primary.get("ota_channels") or ri.get("channels") or [])
        comp_svg = build_comp_set_svg(primary.get("name") or "Hotel", my_bar, [{"name": h["name"], "price": h.get("price")} for h in comp[1:] if h.get("price")])
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "isolated_tenant": True,
            "account": {"id": hid, "username": f"demo_h{hid}", "display_name": primary.get("name"), "primary_hotel_id": hid, "tier": ptier},
            "active_tier": tier_meta,
            "all_tiers": TIER_CATALOG,
            "hidden_by_tier_count": 0,
            "total_assigned_in_account": len(comp),
            "primary_hotel": primary,
            "comp_set": comp,
            "graphics": {"ota_ladder_svg": ota_svg, "comp_set_svg": comp_svg},
            "strategy": {
                "my_bar": my_bar,
                "comp_avg_bar": comp_avg,
                "spread_vs_comp": round(my_bar - comp_avg),
                "undercut_count_in_comp": sum(1 for h in comp if h.get("parity_status") == "UNDERCUT"),
                "recommended_action": "PROTECT PARITY & CAPTURE +4% WKND LIFT",
                "recommended_target_bar": round(my_bar + max(8, my_bar * 0.04)),
                "explanation": f"{primary.get('name')} (${round(my_bar)}/nt) vs {area} comp average (${comp_avg}/nt).",
                "staff_hours_saved_mo": tier_meta["staff_hours_saved_mo"],
                "labor_dollars_saved_mo": tier_meta["labor_dollars_saved_mo"],
                "est_revenue_recovered_mo": tier_meta["est_revenue_recovered_mo"],
            },
            "memory_events": (pitch.get("memory") or {}).get("events") or [],
            "call_logs": [],
            "call_templates": [],
            "tags": [],
            "compression_events": MIAMI_COMPRESSION_EVENTS,
        }))
    if path.startswith("/api/client/"):
        return _reply(start_response, "200 OK", json.dumps({"ok": True, "status": "preview_saved"}))
    if path.startswith("/api/audit/run") and environ.get("REQUEST_METHOD") == "POST":
        hid = str(body.get("hotel_id") or "")
        pitches = json.loads(_load("snapshot_pitches.json"))
        pitch = pitches.get(hid) or next(iter(pitches.values()), {})
        h = pitch.get("hotel") or {}
        ri = pitch.get("rate_intel") or {}
        from hri.audit_engine import build_decision_assistant
        from hri.sales_engine import build_comp_set_svg, build_ota_ladder_svg
        decision = build_decision_assistant(h, ri, ri.get("neighbors") or [], price_monthly=99)
        ota_svg = build_ota_ladder_svg(h.get("name") or "Hotel", ri.get("direct_bar") or 0, ri.get("channels") or [])
        comp_svg = build_comp_set_svg(h.get("name") or "Hotel", ri.get("direct_bar") or decision.get("comp_avg_bar") or 0, ri.get("neighbors") or [])
        emails = [c["value"] for c in (pitch.get("contacts") or []) if c.get("kind") == "email"]
        phones = [c["value"] for c in (pitch.get("contacts") or []) if c.get("kind") == "phone"]
        people = [{"name": c["value"], "title": c.get("person_title") or "GM"} for c in (pitch.get("contacts") or []) if c.get("kind") == "person"]
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "hotel_id": h.get("id", 1),
            "form_autofill": {
                "hotel_id": h.get("id", 1),
                "hotel_name": h.get("name", ""),
                "area": h.get("area", "South Beach"),
                "website": h.get("website", ""),
                "booking_engine": h.get("booking_engine", "Direct Website"),
                "phone": phones[0] if phones else "",
                "important_emails": emails,
                "important_people": people,
            },
            "rate_intel": ri,
            "decision_assistant": decision,
            "graphics": {"ota_ladder_svg": ota_svg, "comp_set_svg": comp_svg},
            "urls": {"demo_url": f"/portal?demo_hotel={h.get('id', 1)}", "audit_url": f"/audit?hotel_id={h.get('id', 1)}"},
            "executive_summary": f"Snapshot Audit for {h.get('name')}: {decision['verdict']} -> Recommended BAR ${decision['recommended_bar']}/nt (+${decision['total_annual_roi']:,}/yr ROI).",
        }))
    if (path.startswith("/api/audit/call") or path.startswith("/api/audit/send-email")) and environ.get("REQUEST_METHOD") == "POST":
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "status": "stateless_preview_run_locally_for_live_dispatch",
            "results": [{"ok": True, "status": "stateless_preview"}],
        }))
    if path.startswith("/api/admin/login") and environ.get("REQUEST_METHOD") == "POST":
        if (body.get("username") or "").strip().lower() == "jasmel" and (body.get("password") or "").strip() == "admin305":
            return _reply(start_response, "200 OK", json.dumps({"ok": True, "token": "mc-admin-jasmel-305", "owner": "Jasmel Acosta"}))
        return _reply(start_response, "401 Unauthorized", json.dumps({"ok": False, "error": "Invalid admin credentials"}))
    if path.startswith("/api/admin/overview"):
        adm_tok = (environ.get("HTTP_X_ADMIN_TOKEN") or (params.get("admin_token") or [""])[0]).strip()
        if adm_tok != "mc-admin-jasmel-305":
            return _reply(start_response, "401 Unauthorized", json.dumps({"ok": False, "error": "Admin login required"}))
        mr = json.loads(_load("snapshot_market_research.json"))
        leads_b = json.loads(_load("snapshot_leads.json"))
        from hri.tenant_engine import TIER_CATALOG, COMPETITOR_COMPARISON_MATRIX
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "owner": "Jasmel Acosta",
            "tiers": TIER_CATALOG,
            "comparison_matrix": COMPETITOR_COMPARISON_MATRIX,
            "accounts": [],
            "campaigns": [],
            "campaign_counts": {"total": 0, "pending_approval": 0, "approved_or_dispatched": 0},
            "leads_bundle": leads_b,
            "market_research": mr,
            "outreach_logs": [],
            "callback_and_auditor_calls": [],
            "outreach_readiness": leads_b.get("readiness") or {},
            "hotels_directory": [{"id": l["hotel_id"], "name": l["name"], "area": l["area"]} for l in (leads_b.get("leads") or [])],
        }))
    if path.startswith("/api/summary"):
        return _reply(start_response, "200 OK", _load("snapshot_summary.json"))
    if path.startswith("/api/ai-pitch"):
        hid = (params.get("hotel_id") or ["4"])[0]
        model = (params.get("model") or ["gemini-2.5-flash-lite"])[0]
        pitches = json.loads(_load("snapshot_pitches.json"))
        pitch = pitches.get(str(hid)) or next(iter(pitches.values()))
        from hri.ai_engine import generate_live_ai_pitch
        ai_res = generate_live_ai_pitch(pitch, preferred_model=model)
        return _reply(start_response, "200 OK", json.dumps({"ok": True, "hotel_id": int(hid), "ai_brief": ai_res}))
    if path.startswith("/api/memory"):
        hid = (params.get("hotel_id") or ["4"])[0]
        pitches = json.loads(_load("snapshot_pitches.json"))
        pitch = pitches.get(str(hid)) or next(iter(pitches.values()))
        return _reply(start_response, "200 OK", json.dumps(pitch.get("memory") or {}))
    if path.startswith("/api/calls"):
        sum_data = json.loads(_load("snapshot_summary.json"))
        if environ.get("REQUEST_METHOD") == "POST":
            return _reply(start_response, "200 OK", json.dumps({
                "ok": True,
                "status": "stateless_demo_use_local_host",
                "reported_occupancy_pct": None,
                "rooms_left": None,
                "quoted_walkin_rate": None,
                "transcript": "Stateless demo deploy — run local server for live voice calls.",
            }))
        return _reply(start_response, "200 OK", json.dumps({
            "calls": sum_data.get("call_logs") or [],
            "templates": sum_data.get("call_templates") or [],
        }))
    if path.startswith("/api/leads"):
        return _reply(start_response, "200 OK", _load("snapshot_leads.json"))
    if path.startswith("/api/market-research"):
        return _reply(start_response, "200 OK", _load("snapshot_market_research.json"))
    if path.startswith("/api/outreach/send") and environ.get("REQUEST_METHOD") == "POST":
        return _reply(start_response, "200 OK", json.dumps({"ok": True, "status": "stateless_demo_use_local_host"}))
    if path.startswith("/api/outreach"):
        leads_data = json.loads(_load("snapshot_leads.json"))
        return _reply(start_response, "200 OK", json.dumps({"readiness": leads_data.get("readiness") or {}, "logs": []}))
    if (path.startswith("/api/opt-out") or path.startswith("/api/hunt-leads")) and environ.get("REQUEST_METHOD") == "POST":
        return _reply(start_response, "200 OK", json.dumps({"ok": True, "status": "stateless_demo_use_local_host"}))
    if path.startswith("/api/my-hotel"):
        return _reply(start_response, "200 OK", json.dumps({"ok": True}))
    if path.startswith("/api/config"):
        if environ.get("REQUEST_METHOD") == "POST":
            return _reply(start_response, "200 OK", json.dumps({"ok": True, "note": "saved on self-hosted instance"}))
        sum_data = json.loads(_load("snapshot_summary.json"))
        return _reply(start_response, "200 OK", json.dumps({"config": sum_data.get("config") or {}, "brief_preview": "Daily HRI Brief Ready."}))
    if path.startswith("/api/send-report") or path.startswith("/api/scrape-now"):
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "telegram_sent": False,
            "telegram_status": "Stateless demo — configure locally",
            "email_sent": False,
            "email_status": "Stateless demo — configure locally",
        }))
    is_single_pitch = path == "/api/pitch" or path.startswith("/api/pitch/")
    if is_single_pitch:
        hid = (params.get("hotel_id") or [""])[0]
        pitches = json.loads(_load("snapshot_pitches.json"))
        if hid in pitches:
            return _reply(start_response, "200 OK", json.dumps(pitches[hid]))
        return _reply(start_response, "404 Not Found",
                      json.dumps({"error": "no pitch for hotel_id", "hotel_id": hid}, indent=1))
    if path.startswith("/api/pitches"):
        return _reply(start_response, "200 OK", _load("snapshot_pitches.json"))
    if path.startswith("/api/hotels"):
        if environ.get("REQUEST_METHOD") == "POST":
            return _reply(start_response, "200 OK", json.dumps({"ok": True, "note": "hotel added on self-hosted instance"}))
        return _reply(start_response, "200 OK", _load("snapshot_hotels.json"))
    if path.startswith("/api/stage"):
        if environ.get("REQUEST_METHOD") == "POST":
            return _reply(start_response, "200 OK", json.dumps({
                "ok": True,
                "note": "stateless deploy: stage updates persist on the self-hosted instance"}))
        return _reply(start_response, "200 OK", _load("snapshot_hotels.json"))
    if path.startswith("/api/rates") and environ.get("REQUEST_METHOD") == "POST":
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True,
            "note": "stateless deploy: writes persist on the self-hosted instance"}))

    return _reply(start_response, "404 Not Found",
                  json.dumps({"error": "unknown endpoint", "path": path}, indent=1))
