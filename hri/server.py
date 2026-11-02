"""Dashboard server — stdlib only (http.server). Serves the themed SPA + JSON API.

Endpoints
  GET /            dashboard HTML
  GET /api/summary        KPIs, movers, prospects, runs
  GET /api/hotels         comp set with latest rates + contacts
  POST /api/rates         manual ingest: {hotel_id, nightly_price, currency, room_type}
"""
import json
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import db as dbmod

DASHBOARD = None  # set by serve()


def _summary(conn, cfg):
    kpis = {
        "hotels": conn.execute("SELECT COUNT(*) c FROM hotels").fetchone()["c"],
        "contacts": conn.execute("SELECT COUNT(*) c FROM contacts").fetchone()["c"],
        "rates": conn.execute("SELECT COUNT(*) c FROM rates").fetchone()["c"],
        "hot_prospects": conn.execute("SELECT COUNT(*) c FROM prospects WHERE tier='hot'").fetchone()["c"],
    }
    rates = dbmod.latest_rates(conn)
    movers = []
    for r in rates:
        if r["price"] and r["prev_price"]:
            pct = (r["price"] - r["prev_price"]) / r["prev_price"] * 100
            movers.append({"name": r["name"], "price": r["price"], "delta_pct": round(pct, 2)})
    prospects = [dict(r) for r in conn.execute(
        """SELECT p.hotel_id, p.score, p.tier, p.signals, h.name, h.area, h.stars, h.est_rooms
           FROM prospects p JOIN hotels h ON h.id=p.hotel_id ORDER BY p.score DESC""")]
    for p in prospects:
        p["signals"] = json.loads(p["signals"] or "[]")
    runs = [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 10")]
    return {"market": cfg["market"], "currency": cfg["currency"], "kpis": kpis,
            "rates": rates, "movers": movers, "prospects": prospects, "runs": runs}


def _hotels(conn):
    out = []
    for h in conn.execute("SELECT * FROM hotels ORDER BY name"):
        h = dict(h)
        h["contacts"] = [dict(r) for r in conn.execute(
            "SELECT kind,value,context FROM contacts WHERE hotel_id=? ORDER BY kind", (h["id"],))]
        h["contact_count"] = len(h["contacts"])
        out.append(h)
    return out


def make_handler(cfg):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/index.html"):
                body = DASHBOARD.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            conn = dbmod.open_db(cfg["database"])
            try:
                if self.path.startswith("/api/summary"):
                    self._json(_summary(conn, cfg))
                elif self.path.startswith("/api/hotels"):
                    self._json({"hotels": _hotels(conn)})
                else:
                    self._json({"error": "not found"}, 404)
            finally:
                conn.close()

        def do_POST(self):
            if not self.path.startswith("/api/rates"):
                self._json({"error": "not found"}, 404)
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                hid = int(body["hotel_id"]); price = float(body["nightly_price"])
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
    global DASHBOARD
    import os
    dash_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "dashboard", "index.html")
    with open(dash_path) as f:
        DASHBOARD = f.read()
    host, port = cfg["dashboard"]["host"], cfg["dashboard"]["port"]
    srv = ThreadingHTTPServer((host, port), make_handler(cfg))
    log(f"dashboard → http://{host}:{port}")
    srv.serve_forever()
