"""Daily Telegram & Email Report Dispatcher + Executive Rate Strategy Brief (`hri/report.py`)."""
import json
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib import request

from . import db as dbmod
from .memory_engine import record_and_analyze_memory


def build_brief(db_path, market="Greater Miami & Beaches"):
    conn = dbmod.open_db(db_path)
    rows = dbmod.latest_rates(conn)
    hotels = conn.execute("SELECT COUNT(*) c FROM hotels").fetchone()["c"]
    total_rates = conn.execute("SELECT COUNT(*) c FROM rates").fetchone()["c"]
    run = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()

    movers = []
    undercuts = []
    strategy_highlights = []

    for r in rows:
        hid = r["hotel_id"]
        mem = record_and_analyze_memory(conn, hid)
        occ = (mem.get("occupancy") or {}).get("est_occupancy_pct", 74)
        pers = (mem.get("occupancy") or {}).get("pricing_personality", "Dynamic Responder")
        rec_action = mem.get("strategy_action", "")

        if r["price"] and r["prev_price"]:
            pct = (r["price"] - r["prev_price"]) / r["prev_price"] * 100
            if abs(pct) >= 1:
                movers.append((r["name"], r["price"], pct, occ, pers))
        if r.get("parity_status") == "UNDERCUT":
            non_direct = [c for c in r.get("ota_channels", []) if c.get("code") != "DIRECT"]
            low = min(non_direct, key=lambda x: x["rate"]) if non_direct else None
            if low:
                undercuts.append((r["name"], r["price"], low["name"], low["rate"], r.get("undercut_pct") or 0, rec_action))
        if rec_action:
            strategy_highlights.append((r["name"], r.get("area") or "", r["price"], mem.get("recommended_bar"), occ, pers, rec_action))

    conn.close()
    movers.sort(key=lambda m: abs(m[2]), reverse=True)
    undercuts.sort(key=lambda u: u[4])

    lines = [
        f"🏨 HRI DAILY RATE, OCCUPANCY & STRATEGY REPORT — {market} — {time.strftime('%b %d, %Y')}",
        f"Tracked Hotels: {hotels} · Rate Observations Memorized: {total_rates} ({len(rows)} properties live)",
    ]
    if run:
        lines.append(f"Latest Scan Run #{run['id']} [{run['status']}] (+{run['rates_new']} rate & occupancy observations)")

    if undercuts:
        lines.append("\n🚨 LIVE OTA PARITY UNDERCUTS (IMMEDIATE RATE FIX REQUIRED):")
        for n, bar, ota, op, pct, act in undercuts[:8]:
            lines.append(f"  ⚠ {n}: Direct BAR ${bar:g} vs {ota} ${op:g} ({pct:+.1f}%) → Strategy: {act}")

    if movers:
        lines.append("\n📊 COMPETITOR RATE MOVES & BEHAVIORAL MEMORY (VS PRIOR SCAN):")
        for n, pr, p, occ, pers in movers[:8]:
            lines.append(f"  {'▲' if p > 0 else '▼'} {n}: ${pr:g}/nt ({p:+.1f}%) · Est. Occ: {occ}% · Behavior: {pers}")

    if strategy_highlights:
        lines.append("\n🧠 AI RATE CHANGE RECOMMENDATIONS (NEXT 48 HOURS):")
        for n, area, cur_p, rec_p, occ, pers, act in strategy_highlights[:8]:
            lines.append(f"  • {n} ({area} · {occ}% Occ): {act}")

    return "\n".join(lines)


def send_telegram(cfg, text):
    tg = cfg.get("telegram") or {}
    tok, chat = (tg.get("bot_token") or "").strip(), (tg.get("chat_id") or "").strip()
    if not tok or not chat:
        return False, "Telegram bot_token or chat_id not configured in Settings"
    try:
        req = request.Request(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            data=json.dumps({"chat_id": chat, "text": text[:4000]}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=12) as r:
            return (r.status == 200), f"Sent to Telegram chat {chat}"
    except Exception as e:
        return False, f"Telegram error: {str(e)[:120]}"


def send_email_report(cfg, text):
    em = cfg.get("email_report") or {}
    host = (em.get("smtp_host") or "").strip()
    port = int(em.get("smtp_port") or 587)
    user = (em.get("smtp_user") or "").strip()
    pw = (em.get("smtp_pass") or "").strip()
    from_addr = (em.get("from_email") or user or "rates@miamihotelintel.com").strip()
    to_addr = (em.get("to_email") or "").strip()

    if not host or not user or not pw or not to_addr:
        return False, "SMTP credentials not configured yet (set them in Settings tab to enable live email dispatch)"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"HRI Daily Hotel Rate, Occupancy & Strategy Report — {time.strftime('%b %d, %Y')}"
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg.attach(MIMEText(text, "plain", "utf-8"))
        html_body = f"<pre style='font:13px/1.55 monospace;color:#0F172A;background:#F8FAFC;padding:18px;border-radius:12px'>{text}</pre>"
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(host, port, timeout=12) as server:
            server.starttls()
            server.login(user, pw)
            server.sendmail(from_addr, [to_addr], msg.as_string())
        return True, f"Sent daily report email to {to_addr}"
    except Exception as e:
        return False, f"SMTP error: {str(e)[:120]}"
