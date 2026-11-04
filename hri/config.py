"""Config loading with sane defaults."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULTS = {
    "market": "Miami Beach, FL",
    "currency": "USD",
    "database": "data/hri.db",
    "stay": {"checkin_days_out": 30, "nights": 3, "adults": 2, "rooms": 1},
    "collector": {
        "max_hotels_per_run": 50,
        "polite_delay_sec": [0.5, 1.5],
        "request_timeout_sec": 18,
        "max_contact_pages_per_hotel": 2,
    },
    "sources": {"hotel_sites": True, "ota": False, "xotelo": True},
    "my_hotel": {
        "hotel_id": 1,
        "custom_name": "",
        "rooms": 45,
        "current_bar": 224,
        "walk_in_rate": 239,
        "min_rate_floor": 159,
        "max_rate_ceiling": 389,
        "resort_fee": 15,
        "current_occupancy_pct": 78,
        "rooms_left_tonight": 10,
    },
    "caller": {
        "provider": "auto_courtesy",
        "shift_window": "23:30 - 04:00 (Overnight Audit)",
        "caller_persona": "Night Audit / Front Desk Courtesy Exchange",
        "default_question": "Courtesy night-audit call-around — checking how your occupancy is looking tonight, how many rooms you have left to sell, and your walk-in BAR rate?",
        "twilio_sid": "",
        "twilio_token": "",
        "twilio_from": "",
        "vapi_api_key": "",
        "record_calls": True,
    },
    "telegram": {"bot_token": "", "chat_id": "", "enabled": True, "schedule_time": "06:00"},
    "email_report": {
        "enabled": True,
        "schedule_time": "06:00",
        "smtp_host": "smtp-relay.brevo.com",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_pass": "",
        "from_email": "rates@miamihotelintel.com",
        "to_email": "jasmel@miamihotelintel.com",
    },
    "dashboard": {"host": "127.0.0.1", "port": 8317, "auth_key": ""},
}


def save(new_cfg, path=None):
    p = path or os.path.join(ROOT, "config.json")
    clean = dict(new_cfg)
    if "database" in clean and os.path.isabs(clean["database"]):
        clean["database"] = "data/hri.db"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)
    return load(p)


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def load(path=None):
    cfg = dict(DEFAULTS)
    p = path or os.path.join(ROOT, "config.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            cfg = _merge(DEFAULTS, json.load(f))
    cfg["database"] = os.path.join(ROOT, cfg["database"]) if not os.path.isabs(cfg["database"]) else cfg["database"]
    os.makedirs(os.path.dirname(cfg["database"]), exist_ok=True)
    return cfg
