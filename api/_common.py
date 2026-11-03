"""Shared WSGI helpers for the Vercel serverless API (underscore files are
not routed by Vercel, so this is import-only)."""
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


def snapshot_app(snapshot_file, extra_ok=False):
    """WSGI app: auth key in ?k=, then serve a committed JSON snapshot."""
    def app(environ, start_response):
        raw = environ.get("RAW_URI") or environ.get("REQUEST_URI") or ""
        params = parse_qs(environ.get("QUERY_STRING", ""))
        if not params and "?" in raw:
            params = parse_qs(raw.split("?", 1)[1])
        key = (params.get("k") or [""])[0]
        if not key or key != _KEY:
            return _reply(start_response, "401 Unauthorized",
                          json.dumps({"error": "auth key required: ?k=<key>"}, indent=1))
        if extra_ok and environ.get("REQUEST_METHOD") == "POST":
            return _reply(start_response, "200 OK", json.dumps({
                "ok": True,
                "note": "stateless deploy: writes persist on the self-hosted instance"}))
        return _reply(start_response, "200 OK", _load(snapshot_file))
    return app
