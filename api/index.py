"""Vercel serverless entrypoint for the HRI dashboard.

Serves committed data snapshots behind the same auth key as the
self-hosted server (hri/server.py). Pure stdlib WSGI — Vercel
auto-detects the `app` callable in api/*.py.

    GET /api/summary?k=<key>   KPIs, movers, prospects, runs
    GET /api/hotels?k=<key>    comp set with contacts
    POST /api/rates            acknowledged, not persisted (stateless)

Set HRI_AUTH_KEY in the Vercel project env; falls back to the dev key.
"""
import json
import os
from urllib.parse import parse_qs

_HERE = os.path.dirname(os.path.abspath(__file__))
_KEY = os.environ.get("HRI_AUTH_KEY", "hri-miami-2026")


def _load(name):
    with open(os.path.join(_HERE, name), encoding="utf-8") as f:
        return f.read().encode("utf-8")


def _reply(start_response, status, body, ctype="application/json; charset=utf-8"):
    headers = [("Content-Type", ctype), ("Cache-Control", "no-store")]
    if isinstance(body, str):
        body = body.encode("utf-8")
    headers.append(("Content-Length", str(len(body))))
    start_response(status, headers)
    return [body]


def app(environ, start_response):
    # Vercel rewrites change PATH_INFO; RAW_URI/REQUEST_URI keep the original path
    raw = environ.get("RAW_URI") or environ.get("REQUEST_URI") or environ.get("PATH_INFO", "/")
    path = raw.split("?")[0]
    params = parse_qs(environ.get("QUERY_STRING", ""))
    if not params and "?" in raw:
        params = parse_qs(raw.split("?", 1)[1])
    key = (params.get("k") or [""])[0]

    if not key or key != _KEY:
        return _reply(start_response, "401 Unauthorized",
                      json.dumps({"error": "auth key required: ?k=<key>"}, indent=1))

    if path.startswith("/api/summary"):
        return _reply(start_response, "200 OK", _load("snapshot_summary.json"))
    if path.startswith("/api/hotels"):
        return _reply(start_response, "200 OK", _load("snapshot_hotels.json"))
    if path.startswith("/api/rates") and environ.get("REQUEST_METHOD") == "POST":
        return _reply(start_response, "200 OK", json.dumps({
            "ok": True, "note": "stateless deploy: persisted on the self-hosted instance"}))

    if path.startswith("/api/debug"):
        return _reply(start_response, "200 OK", json.dumps(
            {k: str(v)[:120] for k, v in sorted(environ.items())}, indent=1))

    if path == "/api/index.py":  # rewrite collapsed the path; inspect what Vercel sent
        return _reply(start_response, "200 OK", json.dumps(
            {k: str(v)[:100] for k, v in sorted(environ.items())}, indent=1))

    return _reply(start_response, "404 Not Found", json.dumps(
        {"error": "unknown endpoint", "path": path, "raw": raw,
         "method": environ.get("REQUEST_METHOD")}, indent=1))
