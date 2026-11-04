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
from .ai_engine import generate_live_ai_pitch, AI_MODEL_BENCHMARKS
from .memory_engine import record_and_analyze_memory, estimate_occupancy_and_personality
from .call_assistant import (
    COURTESY_CALL_TEMPLATES,
    list_call_logs,
    place_or_log_courtesy_call,
    build_my_hotel_comparison,
)
from .report import build_brief, send_telegram, send_email_report

DASH_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "index.html")


def _summary(conn, cfg):
    rates = dbmod.latest_rates(conn)
    undercuts = sum(1 for r in rates if r.get("parity_status") == "UNDERCUT")
    avg_adr = round(sum(r["price"] for r in rates if r.get("price")) / max(1, len(rates))) if rates else 0

    # Enrich each rate row with occupancy & pricing personality from memory engine
    occ_values = []
    for r in rates:
        occ_info = estimate_occupancy_and_personality(
            r, float(r.get("price") or 220), float(r.get("prev_price") or r.get("price") or 210),
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
        "ai_models": AI_MODEL_BENCHMARKS,
        "config": {
            "market": cfg.get("market"),
            "stay": cfg.get("stay"),
            "my_hotel": cfg.get("my_hotel"),
            "caller": cfg.get("caller"),
            "telegram": cfg.get("telegram"),
            "email_report": cfg.get("email_report"),
        },
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
            "SELECT kind,value,context FROM contacts WHERE hotel_id=? ORDER BY kind", (hid,))]
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
        occ_info = estimate_occupancy_and_personality(
            h, float(h["price"] or h.get("price_min") or 220),
            float(h["prev_price"] or h["price"] or 210),
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


def _all_pitches(conn):
    out = {}
    for row in conn.execute("SELECT id FROM hotels ORDER BY id"):
        hid = row["id"]
        out[str(hid)] = build_hotel_pitch(conn, hid)
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

        def do_GET(self):
            if not self._authorized():
                self._json({"error": "unauthorized"}, 401)
                return
            parsed = urlparse(self.path)
            path = parsed.path
            q = parse_qs(parsed.query)
            if path == "/" or path.startswith("/index.html"):
                with open(DASH_PATH, encoding="utf-8") as f:
                    body = f.read().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            conn = dbmod.open_db(cfg["database"])
            try:
                if path.startswith("/api/summary"):
                    self._json(_summary(conn, cfg))
                elif path.startswith("/api/hotels"):
                    self._json({"hotels": _hotels(conn)})
                elif path.startswith("/api/pitches"):
                    self._json(_all_pitches(conn))
                elif path.startswith("/api/pitch"):
                    hid = int((q.get("hotel_id") or [1])[0])
                    self._json(build_hotel_pitch(conn, hid))
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
                        "config": {
                            "market": cfg.get("market"),
                            "stay": cfg.get("stay"),
                            "my_hotel": cfg.get("my_hotel"),
                            "caller": cfg.get("caller"),
                            "telegram": cfg.get("telegram"),
                            "email_report": cfg.get("email_report"),
                        },
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
            path = urlparse(self.path).path
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except Exception:
                self._json({"error": "invalid json"}, 400)
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
                    price_val = float(body.get("initial_bar") or intel.get("direct_price") or 210)
                    dbmod.add_rate(
                        conn, hid, run_id, intel.get("source") or "xotelo",
                        checkin, checkout, price_val, cfg["currency"],
                        intel.get("room_type") or "Standard Room",
                        ota_json=intel.get("channels") or [],
                        parity_status=intel.get("parity_status") or "PARITY",
                        undercut_pct=intel.get("undercut_pct") or 0.0,
                    )
                    dbmod.finish_run(conn, run_id, status="ok", hotels_attempted=1, hotels_ok=1, contacts_new=1, rates_new=1)
                    score_all(conn, log=lambda s: None)
                    record_and_analyze_memory(conn, hid)
                    self._json({"ok": True, "hotel_id": hid, "name": name})
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
                if "market" in body and body["market"]:
                    cfg["market"] = str(body["market"])
                cfgmod.save(cfg)
                self._json({"ok": True, "config": cfg})
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
