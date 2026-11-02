"""Config loading with sane defaults."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "market": "Miami Beach, FL",
    "currency": "USD",
    "database": "data/hri.db",
    "stay": {"checkin_days_out": 30, "nights": 3, "adults": 2, "rooms": 1},
    "collector": {
        "max_hotels_per_run": 12,
        "polite_delay_sec": [2, 5],
        "request_timeout_sec": 25,
        "max_contact_pages_per_hotel": 3,
    },
    "sources": {"hotel_sites": True, "ota": False},
    "telegram": {"bot_token": "", "chat_id": ""},
    "dashboard": {"host": "127.0.0.1", "port": 8317, "auth_key": ""},
}


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load(path=None):
    cfg = dict(DEFAULTS)
    p = path or os.path.join(ROOT, "config.json")
    if os.path.exists(p):
        with open(p) as f:
            cfg = _merge(DEFAULTS, json.load(f))
    cfg["database"] = os.path.join(ROOT, cfg["database"]) if not os.path.isabs(cfg["database"]) else cfg["database"]
    os.makedirs(os.path.dirname(cfg["database"]), exist_ok=True)
    return cfg
