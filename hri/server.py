"""Dashboard server — stdlib only (http.server). Serves the themed SPA + JSON API.

Endpoints
  GET /                       dashboard HTML
  GET /api/summary            KPIs, movers, prospects, runs, pricing tiers
  GET /api/hotels             comp set with latest rates + contacts + parity
  GET /api/pitch?hotel_id=N   personalized call script, SMS, 5-email sequence & ROI math
  GET /api/pitches            all hotels' personalized sales kits (for instant switching)
  POST /api/rates             manual ingest: {hotel_id, nightly_price, currency, room_type}
  POST /api/stage             CRM stage update: {hotel_id, deal_stage}
"""
import json, os
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import db as dbmod
from .sales_engine import build_hotel_pitch, PRICING_TIERS

DASH_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "index.html")


def _summary(conn, cfg):
    rates = dbmod.latest_rates(conn)
    undercuts = sum(1 for r in rates if r.get("parity_status") == "UNDERCUT")
    avg_adr = round(sum(r["price"] for r in rates if r.get("price")) / max(1, len(rates))) if rates else 0

    kpis = {
        "hotels": conn.execute("SELECT COUNT(*) c FROM hotels").fetchone()["c"],
        "contacts": conn.execute("SELECT COUNT(*) c FROM contacts").fetchone()["c"],
        "rates": conn.execute("SELECT COUNT(*) c FROM rates").fetchone()["c"],
        "hot_prospects": conn.execute("SELECT COUNT(*) c FROM prospects WHERE tier='hot'").fetchone()["c"],
        "parity_undercuts": undercuts,
        "avg_adr": avg_adr,
    }
    movers = []
    for r in rates:
        if r["price"] and r["prev_price"]:
            pct = (r["price"] - r["prev_price"]) / r["prev_price"] * 100
            movers.append({
                "hotel_id": r["hotel_id"],
                "name": r["name"],
                "price": r["price"],
                "prev_price": r["prev_price"],
                "delta_pct": round(pct, 1),
                "parity_status": r.get("parity_status"),
                "undercut_pct": r.get("undercut_pct"),
            })
    movers.sort(key=lambda x: abs(x["delta_pct"]), reverse=True)

    prospects = [dict(r) for r in conn.execute(
        """SELECT p.hotel_id, p.score, p.tier, p.signals, p.est_annual_upside,
                  h.name, h.area, h.stars, h.est_rooms, h.booking_engine, h.deal_stage
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
        "pricing_tiers": PRICING_TIERS,
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
                conn.execute("INSERT INTO runs(started,mode,status) VALUES(?,?,?)",
                             (__import__("time").time(), "manual-ingest", "ok"))
                conn.commit()
                run_id = conn.execute("SELECT MAX(id) m FROM runs").fetchone()["m"]
                dbmod.add_rate(conn, hid, run_id, "manual", checkin, checkout,
                               price, body.get("currency", cfg["currency"]), body.get("room_type"))
                self._json({"ok": True, "run_id": run_id})
            finally:
                conn.close()

    return H


def serve(cfg, log=print):
    host, port = cfg["dashboard"]["host"], cfg["dashboard"]["port"]
    srv = ThreadingHTTPServer((host, port), make_handler(cfg))
    log(f"dashboard → http://{host}:{port}")
    srv.serve_forever()
