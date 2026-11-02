"""Best-effort rate capture without an OTA.

Order of attempts per hotel:
  1. schema.org JSON-LD offers on the hotel's own site (often holds nightly rates)
  2. embedded booking-engine payloads (cloudbeds/vevio/bookingengine patterns)
  3. manual ingest via the API (POST /api/rates) — revenue managers often send
     their own BAR sheet; we store it as source='manual'
"""
import json, re, time
from curl_cffi import requests as cr

PRICE_RE = re.compile(r'"price"\s*[:=]\s*"?(\d+(?:\.\d{1,2})?)"?')
CURRENCY_RE = re.compile(r'"priceCurrency"\s*[:=]\s*"?([A-Z]{3})"?')


def scrape_direct_rate(hotel, cfg, log=lambda s: None):
    """Return (price, currency, room_hint) or (None, None, None)."""
    website = hotel.get("website")
    if not website:
        return None, None, None
    try:
        r = cr.get(website, impersonate="chrome", timeout=cfg["collector"]["request_timeout_sec"],
                   headers={"Accept-Language": "en-US,en;q=0.9"})
        html = r.text
    except Exception as e:
        log(f"    ! rate {website}: {type(e).__name__}")
        return None, None, None

    # JSON-LD offers (Hotel reservation)
    for m in re.finditer(r'"@type"\s*:\s*"Offer"(.{0,600}?)\}', html, re.S):
        chunk = m.group(1)
        pm = PRICE_RE.search(chunk)
        if pm:
            cur = (CURRENCY_RE.search(chunk) or [None, "USD"])[1]
            room = re.search(r'"name"\s*:\s*"([^"]{3,60})"', chunk)
            return float(pm.group(1)), cur, room.group(1) if room else None

    # Generic price signals near "per night" copy — weak, low confidence, skip.
    return None, None, None
