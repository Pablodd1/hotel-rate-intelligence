"""Single Vercel WSGI entrypoint for the HRI dashboard API.

Declared in pyproject.toml ([tool.vercel] entrypoint). Receives every
non-static request with the REAL path — no rewrite path-collapsing.

    GET /api/summary?k=<key>   KPIs, movers, prospects, runs
    GET /api/hotels?k=<key>    comp set with contacts
    GET /api/pitches?k=<key>   per-hotel personalized sales kits
    GET /api/ai-pitch?k=<key>  live or cached AI revenue brief
    GET /api/stage?k=<key>     hotels snapshot (stage read)
    POST /api/stage            acknowledged, not persisted (stateless)
    POST /api/rates            acknowledged, not persisted (stateless)

Static dashboard is served from outputDirectory=dashboard by Vercel.
"""
import json
import os
from urllib.parse import parse_qs

_HERE = os.path.dirname(os.path.abspath(__file__))
_API_DIR = os.path.join(_HERE, "api")
_DASH_PATH = os.path.join(_HERE, "dashboard", "index.html")
_KEY = os.environ.get("HRI_AUTH_KEY", "hri-miami-2026")
_dash_cache = None


def _dashboard():
    global _dash_cache
    if _dash_cache is None:
        with open(_DASH_PATH, encoding="utf-8") as f:
            _dash_cache = f.read().encode("utf-8")
    return _dash_cache


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


def app(environ, start_response):
    raw = environ.get("RAW_URI") or environ.get("REQUEST_URI") or environ.get("PATH_INFO", "/")
    path = raw.split("?")[0]
    params = parse_qs(environ.get("QUERY_STRING", ""))
    if not params and "?" in raw:
        params = parse_qs(raw.split("?", 1)[1])
    key = (params.get("k") or [""])[0]

    if not key or key != _KEY:
        return _reply(start_response, "401 Unauthorized",
                      json.dumps({"error": "auth key required: ?k=<key>"}, indent=1))

    if not path.startswith("/api/"):
        return _reply(start_response, "200 OK", _dashboard(),
                      ctype="text/html; charset=utf-8")

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
