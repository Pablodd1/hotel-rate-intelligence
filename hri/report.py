"""Daily Telegram report + plain-text executive & sales brief."""
import json, time
from urllib import request

from . import db as dbmod


def build_brief(db_path, market="Miami Beach"):
    conn = dbmod.open_db(db_path)
    rows = dbmod.latest_rates(conn)
    prospects = [dict(r) for r in conn.execute(
        "SELECT p.*, h.name, h.area FROM prospects p JOIN hotels h ON h.id=p.hotel_id ORDER BY p.score DESC")]
    contacts = conn.execute("SELECT COUNT(*) c FROM contacts").fetchone()["c"]
    hotels = conn.execute("SELECT COUNT(*) c FROM hotels").fetchone()["c"]
    total_rates = conn.execute("SELECT COUNT(*) c FROM rates").fetchone()["c"]
    run = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()

    movers = []
    undercuts = []
    for r in rows:
        if r["price"] and r["prev_price"]:
            pct = (r["price"] - r["prev_price"]) / r["prev_price"] * 100
            if abs(pct) >= 1:
                movers.append((r["name"], r["price"], pct))
        if r.get("parity_status") == "UNDERCUT":
            non_direct = [c for c in r.get("ota_channels", []) if c.get("code") != "DIRECT"]
            low = min(non_direct, key=lambda x: x["rate"]) if non_direct else None
            if low:
                undercuts.append((r["name"], r["price"], low["name"], low["rate"], r.get("undercut_pct") or 0))
    movers.sort(key=lambda m: abs(m[2]), reverse=True)
    undercuts.sort(key=lambda u: u[4])

    lines = [
        f"🏨 HRI — {market} — {time.strftime('%b %d, %Y')}",
        f"hotels: {hotels} · contacts: {contacts} · rate obs: {total_rates} ({len(rows)} properties live)",
    ]
    if run:
        lines.append(f"last run #{run['id']} {run['status']} "
                     f"(+{run['contacts_new']} contacts, +{run['rates_new']} rates)")
    if movers:
        lines.append("\n📊 top rate moves (BAR vs prior scan):")
        lines += [f"  {'▲' if p > 0 else '▼'} {n}: ${pr:g} ({p:+.1f}%)"
                  for n, pr, p in movers[:6]]
    if undercuts:
        lines.append("\n🚨 OTA parity undercuts (highest sales urgency):")
        lines += [f"  ⚠ {n}: BAR ${bar:g} vs {ota} ${op:g} ({pct:+.1f}%)"
                  for n, bar, ota, op, pct in undercuts[:6]]
    hot = [p for p in prospects if p["tier"] == "hot"][:6]
    if hot:
        lines.append("\n🔥 hot B2B prospects to call today:")
        lines += [
            f"  · {p['name']} ({p['area']}) — {p['score']}/100 · +${int(p.get('est_annual_upside') or 45000):,}/yr ROI"
            for p in hot
        ]
    return "\n".join(lines)


def send_telegram(cfg, text):
    tok, chat = cfg["telegram"]["bot_token"], cfg["telegram"]["chat_id"]
    if not tok or not chat:
        return False
    req = request.Request(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data=json.dumps({"chat_id": chat, "text": text}).encode(),
        headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=15) as r:
        return r.status == 200
