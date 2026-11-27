"""Dashboard server — stdlib only (http.server). Serves the Glassy V4 Hotel Rate Scraper & Strategy SPA + JSON API.

Endpoints
  GET /                        Glassy Dashboard V4 HTML
  GET /api/summary             KPIs, movers, runs, memory summary, config preview
  GET /api/hotels              comp set with latest rates + occupancy + pricing personality
  GET /api/pitch?hotel_id=N    hotel rate strategy, memory timeline, recommendations & audit kit
  GET /api/pitches             all hotels' rate strategy & memory kits
  GET /api/memory?hotel_id=N   detailed historical pricing memory, occupancy & neighbor decision logic
  GET /api/config              current scraper, Telegram & Email automation settings
  POST /api/hotels             add or update a hotel in the scraper comp-set (and optionally scrape live rate now)
  POST /api/rates              manual rate observation ingest (+ records into memory_events)
  POST /api/config             update stay horizon, Telegram bot/chat, Email SMTP & daily schedule
  POST /api/send-report        build daily rate/strategy brief and dispatch via Telegram & Email
  POST /api/scrape-now         run a fast live Xotelo + JSON-LD rate & occupancy scan across the comp-set
"""
import json, os, time
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import db as dbmod
from . import config as cfgmod
from .sales_engine import build_hotel_pitch, build_printable_audit_html, PRICING_TIERS, LOCAL_ROUTES, MIAMI_COMPRESSION_EVENTS
from .audit_engine import run_live_hotel_audit, place_auditor_call, send_audit_email_to_leaders
from .sales_chatbot import generate_closer_chat_reply, capture_inbound_callback
from .ai_engine import generate_live_ai_pitch, AI_MODEL_BENCHMARKS
from .memory_engine import record_and_analyze_memory, estimate_occupancy_and_personality
from .call_assistant import (
    COURTESY_CALL_TEMPLATES,
    list_call_logs,
    place_or_log_courtesy_call,
    build_my_hotel_comparison,
)
from .outreach_engine import (
    OFFER_PLANS,
    add_opt_out,
    build_market_research_and_posts,
    get_channel_readiness,
    list_outreach_log,
    list_verified_leads,
    send_or_queue_outreach,
)
from .report import build_brief, send_telegram, send_email_report
from .ops_engine import (
    compute_ai_pricing_plan,
    update_room_ops,
    update_auto_pricing_rules,
    apply_ai_pricing_action,
    send_custom_telegram_ops_alert,
    list_competitor_inquiries,
    create_competitor_inquiry,
    build_room_equivalency_matrix,
    INQUIRY_TEMPLATES,
    NIGHT_AUDIT_WINDOWS,
)
from .tenant_engine import (
    TIER_CATALOG,
    COMPETITOR_COMPARISON_MATRIX,
    ensure_seed_accounts_and_campaigns,
    verify_admin_credentials,
    is_admin_token_valid,
    authenticate_client,
    get_client_by_token,
    register_or_create_client_account,
    update_client_account_admin,
    get_client_portal_data,
    add_client_hotel_tag,
    delete_client_hotel_tag,
    client_scrape_comp_set,
    approve_or_dispatch_campaign,
    get_public_website_payload,
    get_mission_control_overview,
    list_client_accounts,
    list_marketing_campaigns,
)

DASH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
DASH_PATH = os.path.join(DASH_DIR, "index.html")
WEBSITE_PATH = os.path.join(DASH_DIR, "website.html")
CLIENT_PORTAL_PATH = os.path.join(DASH_DIR, "client_portal.html")
MISSION_CONTROL_PATH = os.path.join(DASH_DIR, "mission_control.html")
THEMES_GALLERY_PATH = os.path.join(DASH_DIR, "themes_gallery.html")
APP_DIST_DIR = os.path.join(DASH_DIR, "app")
APP_INDEX_PATH = os.path.join(APP_DIST_DIR, "index.html")


def _summary(conn, cfg):
    rates = dbmod.latest_rates(conn)
    undercuts = sum(1 for r in rates if r.get("parity_status") == "UNDERCUT")
    priced_vals = [float(r["price"]) for r in rates if r.get("price") is not None]
    avg_adr = round(sum(priced_vals) / len(priced_vals)) if priced_vals else 0

    # Enrich each rate row with occupancy & pricing personality from memory engine
    occ_values = []
    for r in rates:
        p_now = float(r["price"]) if r.get("price") is not None else 0.0
        p_prev = float(r["prev_price"]) if r.get("prev_price") is not None else p_now
        occ_info = estimate_occupancy_and_personality(
            r, p_now, p_prev,
            r.get("ota_channels") or [], float(r.get("undercut_pct") or 0.0)
        )
        r["est_occupancy_pct"] = occ_info["est_occupancy_pct"]
        r["pricing_personality"] = occ_info["pricing_personality"]
        r["decision_logic"] = occ_info["decision_logic"]
        occ_values.append(occ_info["est_occupancy_pct"])

    avg_occ = round(sum(occ_values) / max(1, len(occ_values))) if occ_values else 74
    my_hotel_intel = build_my_hotel_comparison(conn, cfg, rates)
    recent_calls = list_call_logs(conn, limit=25)
    mem_count = conn.execute("SELECT COUNT(*) c FROM memory_events").fetchone()["c"]
    rate_count = conn.execute("SELECT COUNT(*) c FROM rates").fetchone()["c"]

    kpis = {
        "hotels": conn.execute("SELECT COUNT(*) c FROM hotels").fetchone()["c"],
        "contacts": conn.execute("SELECT COUNT(*) c FROM contacts").fetchone()["c"],
        "rates": rate_count,
        "memory_events": mem_count + rate_count,
        "calls_logged": len(recent_calls),
        "hot_prospects": conn.execute("SELECT COUNT(*) c FROM prospects WHERE tier='hot'").fetchone()["c"],
        "parity_undercuts": undercuts,
        "avg_adr": avg_adr,
        "avg_occupancy_pct": avg_occ,
    }
    movers = []
    for r in rates:
        if r["price"] and r["prev_price"]:
            pct = (r["price"] - r["prev_price"]) / r["prev_price"] * 100
            movers.append({
                "hotel_id": r["hotel_id"],
                "name": r["name"],
                "area": r.get("area"),
                "price": r["price"],
                "prev_price": r["prev_price"],
                "delta_pct": round(pct, 1),
                "parity_status": r.get("parity_status"),
                "undercut_pct": r.get("undercut_pct"),
                "est_occupancy_pct": r.get("est_occupancy_pct", 74),
                "pricing_personality": r.get("pricing_personality", "Dynamic Responder"),
            })
    movers.sort(key=lambda x: abs(x["delta_pct"]), reverse=True)

    prospects = [dict(r) for r in conn.execute(
        """SELECT p.hotel_id, p.score, p.tier, p.signals, p.est_annual_upside,
                  h.name, h.area, h.stars, h.est_rooms, h.booking_engine, h.deal_stage,
                  h.est_occupancy_pct, h.pricing_personality
           FROM prospects p JOIN hotels h ON h.id=p.hotel_id ORDER BY p.score DESC, p.est_annual_upside DESC""")]
    for p in prospects:
        p["signals"] = json.loads(p["signals"] or "[]")
    runs = [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 10")]
    return {
        "market": cfg["market"],
        "currency": cfg["currency"],
        "kpis": kpis,
        "rates": rates,
        "movers": movers,
        "prospects": prospects,
        "runs": runs,
        "my_hotel": my_hotel_intel,
        "call_logs": recent_calls,
        "call_templates": COURTESY_CALL_TEMPLATES,
        "pricing_tiers": PRICING_TIERS,
        "offer_plans": OFFER_PLANS,
        "outreach_readiness": get_channel_readiness(cfg),
        "ai_models": AI_MODEL_BENCHMARKS,
        "config": cfgmod.sanitize_config_for_ui(cfg),
    }


def _hotels(conn):
    rates_by_id = {r["hotel_id"]: r for r in dbmod.latest_rates(conn)}
    prospects_by_id = {
        r["hotel_id"]: dict(r)
        for r in conn.execute("SELECT * FROM prospects")
    }
    out = []
    for h in conn.execute("SELECT * FROM hotels ORDER BY name"):
        h = dict(h)
        hid = h["id"]
        h["contacts"] = [dict(r) for r in conn.execute(
            "SELECT kind,value,context,verified_status,person_title,source_url FROM contacts WHERE hotel_id=? ORDER BY kind", (hid,))]
        h["contact_count"] = len(h["contacts"])
        r = rates_by_id.get(hid) or {}
        p = prospects_by_id.get(hid) or {}
        h["price"] = r.get("price")
        h["prev_price"] = r.get("prev_price")
        h["delta_pct"] = r.get("delta_pct", 0.0)
        h["checkin"] = r.get("checkin")
        h["parity_status"] = r.get("parity_status")
        h["undercut_pct"] = r.get("undercut_pct", 0.0)
        h["ota_channels"] = r.get("ota_channels", [])
        p_now = float(h["price"]) if h["price"] is not None else 0.0
        p_prev = float(h["prev_price"]) if h["prev_price"] is not None else p_now
        occ_info = estimate_occupancy_and_personality(
            h, p_now, p_prev,
            h["ota_channels"], float(h["undercut_pct"] or 0.0)
        )
        h["est_occupancy_pct"] = occ_info["est_occupancy_pct"]
        h["pricing_personality"] = occ_info["pricing_personality"]
        h["decision_logic"] = occ_info["decision_logic"]
        h["score"] = p.get("score", 0)
        h["tier"] = p.get("tier", "watch")
        h["est_annual_upside"] = p.get("est_annual_upside", 0)
        out.append(h)
    return out


def _all_pitches(conn, custom_price_monthly=None):
    out = {}
    for row in conn.execute("SELECT id FROM hotels ORDER BY id"):
        hid = row["id"]
        out[str(hid)] = build_hotel_pitch(conn, hid, custom_price_monthly=custom_price_monthly)
    return out


def make_handler(cfg):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self):
            key = cfg["dashboard"].get("auth_key") or ""
            if not key:
                return True
            q = parse_qs(urlparse(self.path).query)
            return q.get("k", [""])[0] == key

        def _serve_file(self, filepath, content_type="text/html; charset=utf-8"):
            if not os.path.exists(filepath):
                self._json({"error": "file not found"}, 404)
                return
            with open(filepath, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _is_admin(self, q=None):
            tok = (self.headers.get("X-Admin-Token") or "").strip()
            if not tok and q:
                tok = (q.get("admin_token") or [""])[0].strip()
            return is_admin_token_valid(cfg, tok)

        def _resolve_client(self, conn, q=None, body=None):
            ensure_seed_accounts_and_campaigns(conn, cfg)
            dh = ""
            if q and q.get("demo_hotel"):
                dh = str(q.get("demo_hotel")[0]).strip()
            elif isinstance(body, dict) and body.get("demo_hotel_id"):
                dh = str(body.get("demo_hotel_id")).strip()
            if dh.isdigit():
                auth_res = authenticate_client(conn, "", "", demo_hotel_id=int(dh))
                if auth_res.get("ok"):
                    return auth_res.get("account")
            tok = (self.headers.get("X-Client-Token") or "").strip()
            if not tok and q:
                tok = (q.get("token") or q.get("account_token") or [""])[0].strip()
            if not tok and isinstance(body, dict):
                tok = (body.get("token") or "").strip()
            if tok:
                return get_client_by_token(conn, tok)
            if (q and (q.get("demo") or [""])[0] in ("1", "true")) or (isinstance(body, dict) and body.get("demo")):
                auth_res = authenticate_client(conn, "", "", demo_fallback=True)
                return auth_res.get("account")
            return None

        def do_GET(self):
            if not self._authorized():
                self._json({"error": "unauthorized"}, 401)
                return
            parsed = urlparse(self.path)
            path = parsed.path
            q = parse_qs(parsed.query)

            if path.startswith("/app-assets/"):
                rel = os.path.basename(path)
                asset_fp = os.path.join(APP_DIST_DIR, "app-assets", rel)
                if rel.endswith(".js"):
                    ctype = "application/javascript; charset=utf-8"
                elif rel.endswith(".css"):
                    ctype = "text/css; charset=utf-8"
                elif rel.endswith(".svg"):
                    ctype = "image/svg+xml"
                elif rel.endswith(".png"):
                    ctype = "image/png"
                elif rel.endswith(".jpg") or rel.endswith(".jpeg"):
                    ctype = "image/jpeg"
                elif rel.endswith(".woff2"):
                    ctype = "font/woff2"
                else:
                    ctype = "application/octet-stream"
                self._serve_file(asset_fp, content_type=ctype)
                return

            if path.startswith("/assets/"):
                rel = os.path.basename(path)
                asset_fp = os.path.join(DASH_DIR, "assets", rel)
                if rel.endswith(".mp4"):
                    ctype = "video/mp4"
                elif rel.endswith(".jpg") or rel.endswith(".jpeg"):
                    ctype = "image/jpeg"
                elif rel.endswith(".png"):
                    ctype = "image/png"
                else:
                    ctype = "application/octet-stream"
                self._serve_file(asset_fp, content_type=ctype)
                return

            if path in (
                "/", "/website", "/website.html", "/landing",
                "/pricing", "/contact", "/blog", "/blogs", "/demo",
                "/privacy", "/terms", "/themes", "/themes.html", "/design-versions",
            ):
                target = APP_INDEX_PATH if os.path.exists(APP_INDEX_PATH) else (WEBSITE_PATH if os.path.exists(WEBSITE_PATH) else DASH_PATH)
                self._serve_file(target)
                return

            if path in ("/portal", "/client", "/client_portal.html") or path.startswith("/portal/"):
                target = APP_INDEX_PATH if os.path.exists(APP_INDEX_PATH) else (CLIENT_PORTAL_PATH if os.path.exists(CLIENT_PORTAL_PATH) else DASH_PATH)
                self._serve_file(target)
                return

            if path in ("/mission-control", "/admin"):
                target = MISSION_CONTROL_PATH if os.path.exists(MISSION_CONTROL_PATH) else DASH_PATH
                self._serve_file(target)
                return

            conn = dbmod.open_db(cfg["database"])
            try:
                ensure_seed_accounts_and_campaigns(conn, cfg)
                if path.startswith("/api/public/landing"):
                    self._json(get_public_website_payload(conn, cfg))
                elif path.startswith("/api/client/room-compare"):
                    acc = self._resolve_client(conn, q=q)
                    if not acc:
                        self._json({"ok": False, "error": "Client login required."}, 401)
                        return
                    primary_id = int(acc["primary_hotel_id"])
                    comp_ids = [int(x) for x in (acc.get("assigned_hotel_ids") or [])]
                    tier = (q.get("tier") or ["suite_vs_suite"])[0]
                    occ = (q.get("occ") or ["double"])[0]
                    roll = (q.get("rollaway") or ["0"])[0] in ("1", "true", "yes")
                    self._json(build_room_equivalency_matrix(conn, primary_id, room_tier=tier, occupancy=occ, include_rollaway=roll, comp_hotel_ids=comp_ids))
                elif path.startswith("/api/client/ops"):
                    acc = self._resolve_client(conn, q=q)
                    if not acc:
                        self._json({"ok": False, "error": "Client login required."}, 401)
                        return
                    primary_id = int(acc["primary_hotel_id"])
                    comp_ids = [int(x) for x in (acc.get("assigned_hotel_ids") or [])]
                    plan = compute_ai_pricing_plan(conn, primary_id, comp_hotel_ids=comp_ids)
                    self._json({
                        "ok": True,
                        "plan": plan,
                        "inquiries": list_competitor_inquiries(conn, primary_id),
                        "inquiry_templates": INQUIRY_TEMPLATES,
                        "night_audit_windows": NIGHT_AUDIT_WINDOWS,
                    })
                elif path.startswith("/api/client/portal"):
                    acc = self._resolve_client(conn, q=q)
                    if not acc:
                        self._json({"ok": False, "error": "Client login required. Please sign in to your hotel account."}, 401)
                        return
                    preview_tier = (q.get("preview_tier") or [""])[0].strip() or None
                    self._json(get_client_portal_data(conn, cfg, acc, preview_tier=preview_tier))
                elif path.startswith("/api/admin/overview"):
                    if not self._is_admin(q=q):
                        self._json({"ok": False, "error": "Mission Control Administrator login required."}, 401)
                        return
                    p_str = (q.get("price") or [""])[0]
                    c_price = int(p_str) if p_str.isdigit() else int((cfg.get("outreach") or {}).get("default_price_monthly") or 99)
                    self._json(get_mission_control_overview(conn, cfg, price_monthly=c_price))
                elif path.startswith("/api/summary"):
                    self._json(_summary(conn, cfg))
                elif path.startswith("/api/hotels"):
                    self._json({"hotels": _hotels(conn)})
                elif path.startswith("/api/pitches"):
                    p_str = (q.get("price") or [""])[0]
                    c_price = int(p_str) if p_str.isdigit() else None
                    self._json(_all_pitches(conn, custom_price_monthly=c_price))
                elif path.startswith("/api/pitch"):
                    hid = int((q.get("hotel_id") or [1])[0])
                    p_str = (q.get("price") or [""])[0]
                    c_price = int(p_str) if p_str.isdigit() else None
                    self._json(build_hotel_pitch(conn, hid, custom_price_monthly=c_price))
                elif path.startswith("/api/leads"):
                    p_str = (q.get("price") or [""])[0]
                    c_price = int(p_str) if p_str.isdigit() else int((cfg.get("outreach") or {}).get("default_price_monthly") or 99)
                    res = list_verified_leads(conn, price_monthly=c_price)
                    res["readiness"] = get_channel_readiness(cfg)
                    res["recent_outreach"] = list_outreach_log(conn, limit=40)
                    self._json(res)
                elif path.startswith("/api/outreach"):
                    self._json({
                        "readiness": get_channel_readiness(cfg),
                        "logs": list_outreach_log(conn, limit=60),
                    })
                elif path.startswith("/api/market-research"):
                    self._json(build_market_research_and_posts(conn))
                elif path.startswith("/api/memory"):
                    hid = int((q.get("hotel_id") or [1])[0])
                    self._json(record_and_analyze_memory(conn, hid))
                elif path.startswith("/api/calls"):
                    self._json({
                        "calls": list_call_logs(conn, limit=40),
                        "templates": COURTESY_CALL_TEMPLATES,
                    })
                elif path.startswith("/api/config"):
                    brief_preview = build_brief(cfg["database"], cfg.get("market", "Greater Miami & Beaches"))
                    self._json({
                        "config": cfgmod.sanitize_config_for_ui(cfg),
                        "outreach_readiness": get_channel_readiness(cfg),
                        "brief_preview": brief_preview,
                    })
                elif path.startswith("/api/ai-pitch"):
                    hid = int((q.get("hotel_id") or [1])[0])
                    model = (q.get("model") or ["gemini-2.5-flash-lite"])[0]
                    pitch = build_hotel_pitch(conn, hid)
                    ai_res = generate_live_ai_pitch(pitch, preferred_model=model)
                    self._json({"ok": True, "hotel_id": hid, "ai_brief": ai_res})
                elif path.startswith("/audit") or path.startswith("/api/audit"):
                    hid = int((q.get("hotel_id") or [1])[0])
                    pitch = build_hotel_pitch(conn, hid)
                    body = build_printable_audit_html(pitch).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self._json({"error": "not found"}, 404)
            finally:
                conn.close()

        def do_POST(self):
            if not self._authorized():
                self._json({"error": "unauthorized"}, 401)
                return
            parsed_post = urlparse(self.path)
            path = parsed_post.path
            q_post = parse_qs(parsed_post.query)
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except Exception:
                self._json({"error": "invalid json"}, 400)
                return

            if path.startswith("/api/admin/login"):
                res = verify_admin_credentials(cfg, body.get("username", ""), body.get("password", ""))
                self._json(res, 200 if res.get("ok") else 401)
                return

            if path.startswith("/api/admin/credentials"):
                if not self._is_admin(q=q_post):
                    self._json({"ok": False, "error": "Mission Control Administrator login required."}, 401)
                    return
                admin_cfg = cfg.setdefault("admin_auth", {})
                if body.get("username"):
                    admin_cfg["username"] = str(body["username"]).strip()
                if body.get("password"):
                    admin_cfg["password"] = str(body["password"]).strip()
                if body.get("owner_name"):
                    admin_cfg["owner_name"] = str(body["owner_name"]).strip()
                cfgmod.save(cfg)
                self._json({"ok": True, "username": admin_cfg.get("username")})
                return

            if path.startswith("/api/admin/accounts"):
                if not self._is_admin(q=q_post):
                    self._json({"ok": False, "error": "Mission Control Administrator login required."}, 401)
                    return
                conn = dbmod.open_db(cfg["database"])
                try:
                    ensure_seed_accounts_and_campaigns(conn, cfg)
                    act = (body.get("action") or "create").strip().lower()
                    if act == "update":
                        res = update_client_account_admin(conn, body)
                    else:
                        res = register_or_create_client_account(conn, body, created_by_admin=True)
                    self._json(res, 200 if res.get("ok") else 400)
                finally:
                    conn.close()
                return

            if path.startswith("/api/admin/campaigns"):
                if not self._is_admin(q=q_post):
                    self._json({"ok": False, "error": "Mission Control Administrator login required."}, 401)
                    return
                conn = dbmod.open_db(cfg["database"])
                try:
                    ensure_seed_accounts_and_campaigns(conn, cfg)
                    res = approve_or_dispatch_campaign(conn, cfg, body)
                    self._json(res, 200 if res.get("ok") else 400)
                finally:
                    conn.close()
                return

            if path.startswith("/api/accounts/register"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    ensure_seed_accounts_and_campaigns(conn, cfg)
                    res = register_or_create_client_account(conn, body, created_by_admin=False)
                    self._json(res, 200 if res.get("ok") else 400)
                finally:
                    conn.close()
                return

            if path.startswith("/api/public/chat"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    ensure_seed_accounts_and_campaigns(conn, cfg)
                    res = generate_closer_chat_reply(conn, cfg, body)
                    self._json(res, 200 if res.get("ok") else 400)
                finally:
                    conn.close()
                return

            if path.startswith("/api/public/callback"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    ensure_seed_accounts_and_campaigns(conn, cfg)
                    res = capture_inbound_callback(conn, cfg, body)
                    self._json(res, 200 if res.get("ok") else 400)
                finally:
                    conn.close()
                return

            if path.startswith("/api/audit/run"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    ensure_seed_accounts_and_campaigns(conn, cfg)
                    res = run_live_hotel_audit(conn, cfg, body)
                    self._json(res, 200 if res.get("ok") else 400)
                finally:
                    conn.close()
                return

            if path.startswith("/api/audit/call"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    res = place_auditor_call(conn, cfg, body)
                    self._json(res, 200 if res.get("ok") else 400)
                finally:
                    conn.close()
                return

            if path.startswith("/api/audit/send-email"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    ensure_seed_accounts_and_campaigns(conn, cfg)
                    res = send_audit_email_to_leaders(conn, cfg, body)
                    self._json(res, 200 if res.get("ok") else 400)
                finally:
                    conn.close()
                return

            if path.startswith("/api/client/login"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    ensure_seed_accounts_and_campaigns(conn, cfg)
                    dh = body.get("demo_hotel_id")
                    res = authenticate_client(
                        conn,
                        body.get("username", ""),
                        body.get("password", ""),
                        demo_fallback=bool(body.get("demo")),
                        demo_hotel_id=int(dh) if str(dh or "").isdigit() else None,
                    )
                    self._json(res, 200 if res.get("ok") else 401)
                finally:
                    conn.close()
                return

            if path.startswith("/api/client/"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    acc = self._resolve_client(conn, q=q_post, body=body)
                    if not acc:
                        self._json({"ok": False, "error": "Client login required."}, 401)
                        return
                    if path.startswith("/api/client/ops/inventory"):
                        primary_id = int(acc["primary_hotel_id"])
                        comp_ids = [int(x) for x in (acc.get("assigned_hotel_ids") or [])]
                        ops = update_room_ops(conn, primary_id, body, updated_by=acc.get("display_name") or "Reservations Desk")
                        plan = compute_ai_pricing_plan(conn, primary_id, comp_hotel_ids=comp_ids)
                        self._json({"ok": True, "ops": ops, "plan": plan})
                        return
                    if path.startswith("/api/client/ops/rules"):
                        primary_id = int(acc["primary_hotel_id"])
                        comp_ids = [int(x) for x in (acc.get("assigned_hotel_ids") or [])]
                        rules = update_auto_pricing_rules(conn, primary_id, body)
                        plan = compute_ai_pricing_plan(conn, primary_id, comp_hotel_ids=comp_ids)
                        self._json({"ok": True, "rules": rules, "plan": plan})
                        return
                    if path.startswith("/api/client/ops/apply-pricing"):
                        primary_id = int(acc["primary_hotel_id"])
                        res = apply_ai_pricing_action(conn, cfg, primary_id, body)
                        self._json(res)
                        return
                    if path.startswith("/api/client/ops/telegram-alert"):
                        primary_id = int(acc["primary_hotel_id"])
                        res = send_custom_telegram_ops_alert(
                            conn, cfg, primary_id,
                            message=str(body.get("message") or ""),
                            tags=body.get("tags"),
                        )
                        self._json(res)
                        return
                    if path.startswith("/api/client/ops/comp-inquiry"):
                        primary_id = int(acc["primary_hotel_id"])
                        target_hid = body.get("target_hotel_id")
                        if target_hid and int(target_hid) not in [int(x) for x in (acc.get("assigned_hotel_ids") or [])]:
                            self._json({"ok": False, "error": "Access Denied: target hotel is not in your assigned comp-set.", "forbidden": True}, 403)
                            return
                        res = create_competitor_inquiry(conn, primary_id, body)
                        self._json(res)
                        return
                    if path.startswith("/api/client/scrape"):
                        res = client_scrape_comp_set(conn, cfg, acc)
                        self._json(res)
                        return
                    if path.startswith("/api/client/tags"):
                        if body.get("delete_id"):
                            res = delete_client_hotel_tag(conn, acc, int(body["delete_id"]))
                            self._json(res)
                            return
                        res = add_client_hotel_tag(conn, acc, body)
                        code = 403 if res.get("forbidden") else (200 if res.get("ok") else 400)
                        self._json(res, code)
                        return
                    if path.startswith("/api/client/calls"):
                        target_hid = int(body.get("hotel_id") or acc["primary_hotel_id"])
                        if target_hid not in [int(x) for x in (acc.get("assigned_hotel_ids") or [])]:
                            self._json(
                                {"ok": False, "error": "Access Denied: You can only log/place calls for hotels assigned to your isolated account.", "forbidden": True},
                                403,
                            )
                            return
                        res = place_or_log_courtesy_call(conn, cfg, body)
                        self._json(res)
                        return
                    if path.startswith("/api/client/settings"):
                        body["account_id"] = acc["id"]
                        # Clients cannot arbitrarily assign themselves all 49 hotels; keep their assigned_hotel_ids
                        body.pop("assigned_hotel_ids", None)
                        body.pop("primary_hotel_id", None)
                        res = update_client_account_admin(conn, body)
                        self._json(res, 200 if res.get("ok") else 400)
                        return
                    self._json({"ok": False, "error": "unknown client endpoint"}, 404)
                finally:
                    conn.close()
                return

            if path.startswith("/api/hotels"):
                name = (body.get("name") or "").strip()
                if not name:
                    self._json({"error": "Hotel name is required"}, 400)
                    return
                conn = dbmod.open_db(cfg["database"])
                try:
                    hid = dbmod.upsert_hotel(
                        conn,
                        name=name,
                        area=body.get("area") or "Miami Beach",
                        website=body.get("website") or "",
                        stars=float(body.get("stars") or 3.5),
                        est_rooms=int(body.get("est_rooms") or 45),
                        xotelo_key=(body.get("xotelo_key") or "").strip() or None,
                        booking_engine=body.get("booking_engine") or "Direct / Cloudbeds",
                        price_min=float(body.get("price_min") or 140),
                        price_max=float(body.get("price_max") or 340),
                    )
                    if body.get("email"):
                        dbmod.add_contact(conn, hid, "email", body["email"], "manual_setup")
                    if body.get("phone"):
                        dbmod.add_contact(conn, hid, "phone", body["phone"], "manual_setup")
                    if body.get("address"):
                        dbmod.add_contact(conn, hid, "address", body["address"], "manual_setup")

                    # Immediately scrape or initialize its rate & memory
                    from .rate_engine import scrape_rate_intelligence
                    from .prospects import score_all
                    stay = cfg["stay"]
                    checkin = (date.today() + timedelta(days=stay["checkin_days_out"])).isoformat()
                    checkout = (date.today() + timedelta(days=stay["checkin_days_out"] + stay["nights"])).isoformat()
                    h_row = dict(conn.execute("SELECT * FROM hotels WHERE id=?", (hid,)).fetchone())
                    intel = scrape_rate_intelligence(h_row, cfg, checkin=checkin, checkout=checkout, check_jsonld=False, log=lambda s: None)
                    run_id = dbmod.new_run(conn, mode="add-hotel-scan")
                    manual_bar = body.get("initial_bar")
                    price_val = float(manual_bar) if manual_bar else intel.get("direct_price")
                    rates_new = 0
                    if price_val is not None:
                        dbmod.add_rate(
                            conn, hid, run_id,
                            "manual" if manual_bar else (intel.get("source") or "xotelo"),
                            checkin, checkout, float(price_val), cfg["currency"],
                            intel.get("room_type") or "Standard Room",
                            ota_json=intel.get("channels") or [],
                            parity_status=intel.get("parity_status") or "PARITY",
                            undercut_pct=intel.get("undercut_pct") or 0.0,
                        )
                        rates_new = 1
                    dbmod.finish_run(conn, run_id, status="ok", hotels_attempted=1, hotels_ok=1 if rates_new else 0, contacts_new=1, rates_new=rates_new)
                    score_all(conn, log=lambda s: None)
                    record_and_analyze_memory(conn, hid)
                    self._json({"ok": True, "hotel_id": hid, "name": name, "rates_new": rates_new})
                finally:
                    conn.close()
                return

            if path.startswith("/api/calls"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    if body.get("batch"):
                        area = body.get("area") or ""
                        sql = "SELECT id FROM hotels WHERE area=? ORDER BY id LIMIT 8" if area else "SELECT id FROM hotels ORDER BY id LIMIT 8"
                        hrows = conn.execute(sql, (area,) if area else ()).fetchall()
                        results = []
                        for hr in hrows:
                            results.append(place_or_log_courtesy_call(conn, cfg, {"hotel_id": hr["id"], "caller_mode": "Overnight Batch Auto-Caller"}))
                        self._json({"ok": True, "batch_count": len(results), "results": results})
                    else:
                        res = place_or_log_courtesy_call(conn, cfg, body)
                        self._json(res)
                finally:
                    conn.close()
                return

            if path.startswith("/api/my-hotel"):
                cfg.setdefault("my_hotel", {}).update(body)
                cfgmod.save(cfg)
                if body.get("hotel_id") and body.get("current_bar"):
                    conn = dbmod.open_db(cfg["database"])
                    try:
                        hid = int(body["hotel_id"])
                        bar_v = float(body["current_bar"])
                        occ_v = int(body.get("current_occupancy_pct") or 78)
                        conn.execute("UPDATE hotels SET est_occupancy_pct=? WHERE id=?", (occ_v, hid))
                        conn.commit()
                    finally:
                        conn.close()
                self._json({"ok": True, "my_hotel": cfg["my_hotel"]})
                return

            if path.startswith("/api/config"):
                if "stay" in body and isinstance(body["stay"], dict):
                    cfg["stay"].update(body["stay"])
                if "my_hotel" in body and isinstance(body["my_hotel"], dict):
                    cfg.setdefault("my_hotel", {}).update(body["my_hotel"])
                if "caller" in body and isinstance(body["caller"], dict):
                    cfg.setdefault("caller", {}).update(body["caller"])
                if "telegram" in body and isinstance(body["telegram"], dict):
                    cfg.setdefault("telegram", {}).update(body["telegram"])
                if "email_report" in body and isinstance(body["email_report"], dict):
                    cfg.setdefault("email_report", {}).update(body["email_report"])
                if "outreach" in body and isinstance(body["outreach"], dict):
                    cfg.setdefault("outreach", {}).update(body["outreach"])
                if "market" in body and body["market"]:
                    cfg["market"] = str(body["market"])
                cfgmod.save(cfg)
                self._json({"ok": True, "config": cfg})
                return

            if path.startswith("/api/outreach/send"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    res = send_or_queue_outreach(conn, cfg, body)
                    self._json(res)
                finally:
                    conn.close()
                return

            if path.startswith("/api/opt-out"):
                conn = dbmod.open_db(cfg["database"])
                try:
                    ok = add_opt_out(conn, body.get("value", ""), body.get("channel", ""), body.get("reason", "manual_opt_out"))
                    self._json({"ok": ok, "value": body.get("value", "")})
                finally:
                    conn.close()
                return

            if path.startswith("/api/hunt-leads"):
                from .lead_hunter import run_lead_hunter
                rid = run_lead_hunter(cfg, quick=bool(body.get("quick")), log=lambda s: None)
                self._json({"ok": True, "run_id": rid})
                return

            if path.startswith("/api/send-report"):
                brief = build_brief(cfg["database"], cfg.get("market", "Greater Miami & Beaches"))
                tg_ok, tg_msg = send_telegram(cfg, brief)
                em_ok, em_msg = send_email_report(cfg, brief)
                self._json({
                    "ok": True,
                    "telegram_sent": tg_ok,
                    "telegram_status": tg_msg,
                    "email_sent": em_ok,
                    "email_status": em_msg,
                    "brief": brief,
                })
                return

            if path.startswith("/api/scrape-now"):
                from .collector import run_collect
                run_id = run_collect(cfg, crawl_sites=False, log=lambda s: None)
                self._json({"ok": True, "run_id": run_id})
                return

            if path.startswith("/api/stage"):
                try:
                    hid = int(body["hotel_id"])
                    stage = str(body["deal_stage"])
                except (KeyError, ValueError):
                    self._json({"error": "need hotel_id + deal_stage"}, 400)
                    return
                conn = dbmod.open_db(cfg["database"])
                try:
                    conn.execute("UPDATE hotels SET deal_stage=? WHERE id=?", (stage, hid))
                    conn.commit()
                    self._json({"ok": True, "hotel_id": hid, "deal_stage": stage})
                finally:
                    conn.close()
                return

            if not path.startswith("/api/rates"):
                self._json({"error": "not found"}, 404)
                return
            try:
                hid = int(body["hotel_id"])
                price = float(body["nightly_price"])
            except (KeyError, ValueError):
                self._json({"error": "need hotel_id + nightly_price"}, 400)
                return
            stay = cfg["stay"]
            checkin = (date.today() + timedelta(days=stay["checkin_days_out"])).isoformat()
            checkout = (date.today() + timedelta(days=stay["checkin_days_out"] + stay["nights"])).isoformat()
            conn = dbmod.open_db(cfg["database"])
            try:
                prev_row = conn.execute("SELECT nightly_price FROM rates WHERE hotel_id=? ORDER BY id DESC LIMIT 1", (hid,)).fetchone()
                prev_p = float(prev_row["nightly_price"]) if prev_row and prev_row["nightly_price"] else price
                delta_pct = round(((price - prev_p) / prev_p) * 100, 1) if prev_p else 0.0

                conn.execute("INSERT INTO runs(started,mode,status) VALUES(?,?,?)",
                             (time.time(), "manual-rate-memory", "ok"))
                conn.commit()
                run_id = conn.execute("SELECT MAX(id) m FROM runs").fetchone()["m"]
                dbmod.add_rate(conn, hid, run_id, "manual", checkin, checkout,
                               price, body.get("currency", cfg["currency"]), body.get("room_type"))
                est_occ = int(body.get("est_occupancy_pct") or 76)
                conn.execute(
                    """INSERT INTO memory_events(hotel_id,event_type,old_price,new_price,delta_pct,est_occupancy_pct,competitor_pattern,ai_recommendation,recorded_at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (hid, "rate_change", prev_p, price, delta_pct, est_occ, "MANUAL_OBSERVATION",
                     body.get("notes") or f"Memorized rate move ${prev_p:.0f} → ${price:.0f} ({delta_pct:+.1f}%)", time.time())
                )
                conn.commit()
                self._json({"ok": True, "run_id": run_id})
            finally:
                conn.close()

    return H


def serve(cfg, log=print):
    host, port = cfg["dashboard"]["host"], cfg["dashboard"]["port"]
    srv = ThreadingHTTPServer((host, port), make_handler(cfg))
    log(f"dashboard → http://{host}:{port}")
    srv.serve_forever()
