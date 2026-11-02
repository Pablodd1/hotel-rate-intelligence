"""Daily Telegram report + plain-text brief."""
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
    run = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()

    movers = []
    for r in rows:
        if r["price"] and r["prev_price"]:
            pct = (r["price"] - r["prev_price"]) / r["prev_price"] * 100
            if abs(pct) >= 1:
                movers.append((r["name"], r["price"], pct))
    movers.sort(key=lambda m: m[2])

    lines = [f"🏨 HRI — {market} — {time.strftime('%b %d')}",
             f"hotels: {hotels} · contacts: {contacts} · rates: {len(rows)}"]
    if run:
        lines.append(f"last run #{run['id']} {run['status']} "
                     f"(+{run['contacts_new']} contacts, +{run['rates_new']} rates)")
    if movers:
        lines.append("rate moves:")
        lines += [f"  {'▲' if p > 0 else '▼'} {n}: ${pr:g} ({p:+.1f}%)"
                  for n, pr, p in movers[:5]]
    hot = [p for p in prospects if p["tier"] == "hot"][:5]
    if hot:
        lines.append("hot prospects:")
        lines += [f"  · {p['name']} ({p['area']}) — {p['score']}/100" for p in hot]
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
