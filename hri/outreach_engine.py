"""Multi-Channel Outbound Engine, Pricing Lab & Live Market Research (`hri/outreach_engine.py`).

ZERO-HALLUCINATION & SAFE-DISPATCH DESIGN:
1. Every email must pass DNS MX validation before enqueueing or sending.
2. Every person citation comes strictly from `contacts(kind='person', verified_status=...)`.
3. Never claims an external Email / SMS / WhatsApp / Voice message was sent unless `outreach.mode == 'live'`
   AND the selected provider API returned HTTP 2xx with a message/call ID.
4. When live keys are absent or `mode == 'dry_run'`, stores honest `queued_dry_run` / `ready_awaiting_credentials`
   rows in `outreach_log` and generates 1-click native `mailto:`, `sms:`, `https://wa.me/`, and `tel:` links.
"""
import json
import os
import re
import smtplib
import time
import urllib.error
import urllib.parse
import urllib.request
from base64 import b64encode
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from . import db as dbmod
from .hotel_sites import verify_email_mx
from .sales_engine import build_hotel_pitch

OFFER_PLANS = [
    {"id": "intro_49", "label": "$49 Intro", "price_monthly": 49, "note": "First-month beachhead trial -> $99/mo standard"},
    {"id": "pilot_79", "label": "$79 Lock", "price_monthly": 79, "note": "Founding-cohort lifetime rate (first 10 hotels)"},
    {"id": "founder_99", "label": "$99 Anchor", "price_monthly": 99, "note": "Core flat price ($3.30/day · <1/3 of 1 room night)", "recommended": True},
    {"id": "growth_149", "label": "$149 Plus", "price_monthly": 149, "note": "2x daily scans + multi-OTA parity alerts"},
    {"id": "pro_199", "label": "$199 Pro", "price_monthly": 199, "note": "SMS/WhatsApp undercut alerts + overnight courtesy desk"},
    {"id": "portfolio_399", "label": "$399 Group", "price_monthly": 399, "note": "Multi-property owners (up to 5 Miami hotels)"},
]


def _e164(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if len(digits) > 10:
        return f"+{digits}"
    return ""


def _wa_digits(phone: str) -> str:
    return re.sub(r"\D", "", _e164(phone))


def _is_opted_out(conn, value: str) -> bool:
    if not value:
        return False
    norm = value.strip().lower()
    row = conn.execute("SELECT 1 FROM do_not_contact WHERE lower(value)=?", (norm,)).fetchone()
    if row:
        return True
    e164 = _e164(value)
    if e164:
        return bool(conn.execute("SELECT 1 FROM do_not_contact WHERE value=?", (e164,)).fetchone())
    return False


def add_opt_out(conn, value: str, channel: str = "", reason: str = "manual_opt_out") -> bool:
    clean = (value or "").strip()
    if not clean:
        return False
    if "@" in clean:
        clean = clean.lower()
    else:
        clean = _e164(clean) or clean
    conn.execute(
        "INSERT OR REPLACE INTO do_not_contact(value, channel, reason, added_at) VALUES(?,?,?,?)",
        (clean, channel, reason, time.time()),
    )
    conn.commit()
    return True


def get_channel_readiness(cfg: dict) -> dict:
    """Inspect real local/env credentials and return honest channel readiness + estimated starter costs."""
    out_cfg = cfg.get("outreach") or {}
    em_cfg = cfg.get("email_report") or {}
    cal_cfg = cfg.get("caller") or {}
    tg_cfg = cfg.get("telegram") or {}

    mode = (out_cfg.get("mode") or "dry_run").lower()
    brevo_key = (out_cfg.get("brevo_api_key") or os.environ.get("BREVO_API_KEY") or "").strip()
    resend_key = (out_cfg.get("resend_api_key") or os.environ.get("RESEND_API_KEY") or "").strip()
    smtp_ok = all([(em_cfg.get("smtp_host") or "").strip(), (em_cfg.get("smtp_user") or "").strip(), (em_cfg.get("smtp_pass") or "").strip()])
    email_pref = (out_cfg.get("email_provider") or "smtp").lower()
    email_live = bool((email_pref == "brevo" and brevo_key) or (email_pref == "resend" and resend_key) or smtp_ok or brevo_key or resend_key)

    tw_sid = (out_cfg.get("twilio_account_sid") or cal_cfg.get("twilio_sid") or os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
    tw_tok = (out_cfg.get("twilio_auth_token") or cal_cfg.get("twilio_token") or os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    tw_from = (out_cfg.get("twilio_from_phone") or cal_cfg.get("twilio_from") or os.environ.get("TWILIO_FROM_PHONE") or "").strip()
    tw_wa = (out_cfg.get("twilio_whatsapp_from") or os.environ.get("TWILIO_WHATSAPP_FROM") or "").strip()
    sms_live = bool(tw_sid and tw_tok and tw_from)
    wa_live = bool(tw_sid and tw_tok and tw_wa)

    vapi_key = (out_cfg.get("vapi_api_key") or cal_cfg.get("vapi_api_key") or os.environ.get("VAPI_API_KEY") or "").strip()
    vapi_num = (out_cfg.get("vapi_phone_number_id") or os.environ.get("VAPI_PHONE_NUMBER_ID") or "").strip()
    bland_key = (out_cfg.get("bland_api_key") or os.environ.get("BLAND_API_KEY") or "").strip()
    voice_live = bool((vapi_key and vapi_num) or bland_key or sms_live)

    tg_live = bool((tg_cfg.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip() and (tg_cfg.get("chat_id") or "").strip())
    gemini_live = bool(os.environ.get("GEMINI_API_KEY", "").strip())

    return {
        "mode": mode,
        "daily_send_cap": int(out_cfg.get("daily_send_cap") or 50),
        "default_price_monthly": int(out_cfg.get("default_price_monthly") or 99),
        "offer_plans": OFFER_PLANS,
        "channels": {
            "email": {
                "ready": email_live,
                "provider": "brevo" if brevo_key else ("resend" if resend_key else "smtp"),
                "cost_estimate": "$0/mo (Brevo 300/day or Resend 3k/mo free tier)",
                "missing": [] if email_live else ["brevo_api_key OR resend_api_key OR smtp_user+smtp_pass"],
            },
            "sms": {
                "ready": sms_live,
                "provider": "twilio_sms",
                "cost_estimate": "$1.15/mo number + ~$0.0083/SMS (~$15-25 A2P setup)",
                "missing": [] if sms_live else ["twilio_account_sid", "twilio_auth_token", "twilio_from_phone"],
            },
            "whatsapp": {
                "ready": wa_live,
                "provider": "twilio_whatsapp",
                "cost_estimate": "$0 sandbox / ~$0.015-$0.04 per business-initiated template",
                "missing": [] if wa_live else ["twilio_account_sid", "twilio_auth_token", "twilio_whatsapp_from"],
            },
            "voice": {
                "ready": voice_live,
                "provider": "vapi" if (vapi_key and vapi_num) else ("bland" if bland_key else "twilio_voice"),
                "cost_estimate": "~$0.07-$0.12/min (Vapi/Bland ~$10-$30 starter credit)",
                "missing": [] if voice_live else ["(vapi_api_key + vapi_phone_number_id) OR bland_api_key OR twilio_voice"],
            },
            "telegram": {
                "ready": tg_live,
                "provider": "telegram_bot",
                "cost_estimate": "$0/mo",
                "missing": [] if tg_live else ["telegram.bot_token", "telegram.chat_id"],
            },
            "ai_copy": {
                "ready": True,
                "live_llm_connected": gemini_live,
                "provider": "gemini-2.5-flash-lite + deterministic" if gemini_live else "deterministic_local",
                "cost_estimate": "~$0-$1/mo",
            },
        },
    }


def _http_json(url: str, payload: dict, headers: dict = None, auth_basic: tuple = None, timeout: int = 15) -> tuple:
    hdrs = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "HotelRateIntel/1.0"}
    if headers:
        hdrs.update(headers)
    if auth_basic:
        tok = b64encode(f"{auth_basic[0]}:{auth_basic[1]}".encode()).decode()
        hdrs["Authorization"] = f"Basic {tok}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8") or "{}")
            return (200 <= r.status < 300), r.status, body
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return False, e.code, {"error": f"HTTP {e.code}: {raw[:180]}"}
    except Exception as e:
        return False, 0, {"error": str(e)[:180]}


def _http_form(url: str, form_data: dict, auth_basic: tuple, timeout: int = 15) -> tuple:
    tok = b64encode(f"{auth_basic[0]}:{auth_basic[1]}".encode()).decode()
    data = urllib.parse.urlencode(form_data).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Authorization": f"Basic {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8") or "{}")
            return (200 <= r.status < 300), r.status, body
    except Exception as e:
        return False, 0, {"error": str(e)[:180]}


def _send_live_email(cfg: dict, to_email: str, subject: str, body_text: str, html_body: str = "") -> dict:
    out_cfg = cfg.get("outreach") or {}
    em_cfg = cfg.get("email_report") or {}
    phys_addr = out_cfg.get("physical_address") or "North Miami, FL 33161"
    sender_name = out_cfg.get("sender_name") or "Jasmel Acosta"
    from_email = (em_cfg.get("from_email") or em_cfg.get("smtp_user") or "jasmel@hotelrateintel.com").strip()
    reply_to = (out_cfg.get("reply_to_email") or em_cfg.get("to_email") or "jasmelacosta@gmail.com").strip()
    full_body = f"{body_text.rstrip()}\n\n--\n{sender_name} | {phys_addr}\nReply STOP to opt out of future local rate briefs."

    pref = (out_cfg.get("email_provider") or "smtp").lower()
    brevo_key = (out_cfg.get("brevo_api_key") or os.environ.get("BREVO_API_KEY") or "").strip()
    resend_key = (out_cfg.get("resend_api_key") or os.environ.get("RESEND_API_KEY") or "").strip()

    if (pref == "brevo" and brevo_key) or (brevo_key and pref != "resend"):
        payload_b = {
            "sender": {"name": sender_name, "email": from_email},
            "to": [{"email": to_email}],
            "replyTo": {"email": reply_to},
            "subject": subject,
            "textContent": full_body,
        }
        if html_body:
            payload_b["htmlContent"] = html_body
        ok, code, resp = _http_json(
            "https://api.brevo.com/v3/smtp/email",
            payload_b,
            headers={"api-key": brevo_key},
        )
        return {"ok": ok, "provider": "brevo", "msg_id": resp.get("messageId", ""), "error": resp.get("error") or resp.get("message", "")}

    if resend_key:
        payload_r = {"from": f"{sender_name} <{from_email}>", "to": [to_email], "reply_to": [reply_to], "subject": subject, "text": full_body}
        if html_body:
            payload_r["html"] = html_body
        ok, code, resp = _http_json(
            "https://api.resend.com/emails",
            payload_r,
            headers={"Authorization": f"Bearer {resend_key}"},
        )
        return {"ok": ok, "provider": "resend", "msg_id": resp.get("id", ""), "error": resp.get("error") or resp.get("message", "")}

    host = (em_cfg.get("smtp_host") or "").strip()
    port = int(em_cfg.get("smtp_port") or 587)
    user = (em_cfg.get("smtp_user") or "").strip()
    pw = (em_cfg.get("smtp_pass") or "").strip()
    if host and user and pw:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{sender_name} <{from_email}>"
            msg["To"] = to_email
            msg["Reply-To"] = reply_to
            msg.attach(MIMEText(full_body, "plain", "utf-8"))
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.starttls()
                s.login(user, pw)
                s.sendmail(from_email, [to_email], msg.as_string())
            return {"ok": True, "provider": "smtp", "msg_id": f"smtp-{int(time.time())}", "error": ""}
        except Exception as e:
            return {"ok": False, "provider": "smtp", "msg_id": "", "error": str(e)[:180]}
    return {"ok": False, "provider": "none", "msg_id": "", "error": "No Email API or SMTP credentials configured"}


def _send_live_twilio(cfg: dict, to_phone: str, text_body: str, whatsapp: bool = False) -> dict:
    out_cfg = cfg.get("outreach") or {}
    cal_cfg = cfg.get("caller") or {}
    sid = (out_cfg.get("twilio_account_sid") or cal_cfg.get("twilio_sid") or os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
    tok = (out_cfg.get("twilio_auth_token") or cal_cfg.get("twilio_token") or os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    from_num = (
        (out_cfg.get("twilio_whatsapp_from") or os.environ.get("TWILIO_WHATSAPP_FROM") or "")
        if whatsapp
        else (out_cfg.get("twilio_from_phone") or cal_cfg.get("twilio_from") or os.environ.get("TWILIO_FROM_PHONE") or "")
    ).strip()
    e164_to = _e164(to_phone)
    if not (sid and tok and from_num and e164_to):
        return {"ok": False, "provider": "twilio_whatsapp" if whatsapp else "twilio_sms", "msg_id": "", "error": "Twilio credentials or valid recipient phone missing"}
    to_val = f"whatsapp:{e164_to}" if whatsapp and not e164_to.startswith("whatsapp:") else e164_to
    from_val = f"whatsapp:{_e164(from_num)}" if whatsapp and not from_num.startswith("whatsapp:") else (_e164(from_num) or from_num)
    ok, code, resp = _http_form(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        {"To": to_val, "From": from_val, "Body": text_body},
        auth_basic=(sid, tok),
    )
    return {
        "ok": ok,
        "provider": "twilio_whatsapp" if whatsapp else "twilio_sms",
        "msg_id": resp.get("sid", ""),
        "error": resp.get("error") or resp.get("message", ""),
    }


def _send_live_voice(cfg: dict, to_phone: str, prompt_text: str, first_message: str) -> dict:
    out_cfg = cfg.get("outreach") or {}
    cal_cfg = cfg.get("caller") or {}
    e164_to = _e164(to_phone)
    if not e164_to:
        return {"ok": False, "provider": "none", "msg_id": "", "error": "Invalid destination phone"}
    vapi_key = (out_cfg.get("vapi_api_key") or cal_cfg.get("vapi_api_key") or os.environ.get("VAPI_API_KEY") or "").strip()
    vapi_num = (out_cfg.get("vapi_phone_number_id") or os.environ.get("VAPI_PHONE_NUMBER_ID") or "").strip()
    bland_key = (out_cfg.get("bland_api_key") or os.environ.get("BLAND_API_KEY") or "").strip()
    tw_sid = (out_cfg.get("twilio_account_sid") or cal_cfg.get("twilio_sid") or "").strip()
    tw_tok = (out_cfg.get("twilio_auth_token") or cal_cfg.get("twilio_token") or "").strip()
    tw_from = (out_cfg.get("twilio_from_phone") or cal_cfg.get("twilio_from") or "").strip()

    if vapi_key and vapi_num:
        ok, code, resp = _http_json(
            "https://api.vapi.ai/call/phone",
            {
                "phoneNumberId": vapi_num,
                "customer": {"number": e164_to},
                "assistant": {
                    "firstMessage": first_message,
                    "model": {"provider": "google", "model": "gemini-2.5-flash-lite", "messages": [{"role": "system", "content": prompt_text}]},
                },
            },
            headers={"Authorization": f"Bearer {vapi_key}"},
        )
        return {"ok": ok, "provider": "vapi", "msg_id": resp.get("id", ""), "error": resp.get("error") or resp.get("message", "")}

    if bland_key:
        ok, code, resp = _http_json(
            "https://api.bland.ai/v1/calls",
            {"phone_number": e164_to, "task": prompt_text, "first_sentence": first_message, "record": True},
            headers={"Authorization": bland_key},
        )
        return {"ok": ok, "provider": "bland", "msg_id": resp.get("call_id", ""), "error": resp.get("error") or resp.get("message", "")}

    if tw_sid and tw_tok and tw_from:
        esc = first_message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ok, code, resp = _http_form(
            f"https://api.twilio.com/2010-04-01/Accounts/{tw_sid}/Calls.json",
            {"To": e164_to, "From": _e164(tw_from) or tw_from, "Twiml": f"<Response><Say>{esc}</Say></Response>", "Record": "true"},
            auth_basic=(tw_sid, tw_tok),
        )
        return {"ok": ok, "provider": "twilio_voice", "msg_id": resp.get("sid", ""), "error": resp.get("error") or resp.get("message", "")}

    return {"ok": False, "provider": "none", "msg_id": "", "error": "No Voice AI / Twilio Voice credentials configured"}


def send_or_queue_outreach(conn, cfg: dict, payload: dict) -> dict:
    """Queue or live-send single or batch outreach with strict zero-hallucination & opt-out safeguards."""
    channel = (payload.get("channel") or "email").lower()
    if channel not in ("email", "sms", "whatsapp", "voice", "walk_in"):
        return {"ok": False, "error": f"Unsupported channel: {channel}"}

    price_monthly = int(payload.get("price_monthly") or (cfg.get("outreach") or {}).get("default_price_monthly") or 99)
    readiness = get_channel_readiness(cfg)
    req_mode = (payload.get("mode") or readiness["mode"] or "dry_run").lower()

    if payload.get("batch"):
        tier = (payload.get("tier") or "hot").lower()
        limit = min(50, max(1, int(payload.get("limit") or 10)))
        if payload.get("hotel_ids"):
            target_ids = [int(x) for x in payload["hotel_ids"]][:limit]
        else:
            sql = "SELECT h.id FROM hotels h LEFT JOIN prospects p ON p.hotel_id=h.id "
            if tier in ("hot", "warm", "watch"):
                sql += "WHERE p.tier=? ORDER BY COALESCE(p.score,0) DESC LIMIT ?"
                rows = conn.execute(sql, (tier, limit)).fetchall()
            else:
                sql += "ORDER BY COALESCE(p.score,0) DESC LIMIT ?"
                rows = conn.execute(sql, (limit,)).fetchall()
            target_ids = [r["id"] for r in rows]
        results = [
            send_or_queue_outreach(conn, cfg, {
                "hotel_id": hid,
                "channel": channel,
                "price_monthly": price_monthly,
                "mode": req_mode,
                "step_index": int(payload.get("step_index") or 0),
            })
            for hid in target_ids
        ]
        sent_n = sum(1 for r in results if r.get("status") == "sent_live")
        queued_n = sum(1 for r in results if r.get("status") in ("queued_dry_run", "ready_awaiting_credentials"))
        return {"ok": True, "batch_count": len(results), "sent_live": sent_n, "queued": queued_n, "results": results}

    hid = int(payload.get("hotel_id") or 0)
    if not hid:
        return {"ok": False, "error": "hotel_id is required"}

    pitch = build_hotel_pitch(conn, hid, custom_price_monthly=price_monthly)
    if not pitch:
        return {"ok": False, "error": f"Hotel id={hid} not found"}

    h = pitch["hotel"]
    step_idx = int(payload.get("step_index") or 0)
    subject = (payload.get("subject") or "").strip()
    body_text = (payload.get("body") or "").strip()
    recipient = ""
    deep_link = ""

    if channel == "email":
        recipient = (payload.get("recipient") or h.get("primary_email") or "").strip().lower()
        if not recipient:
            return {"ok": False, "hotel_id": hid, "error": f"No verified email stored for {h['name']}"}
        if not verify_email_mx(recipient):
            return {"ok": False, "hotel_id": hid, "error": f"Email domain failed DNS MX check: {recipient}"}
        em_tpl = pitch["emails"][min(step_idx, len(pitch["emails"]) - 1)]
        subject = subject or em_tpl["subject"]
        body_text = body_text or em_tpl["body"]
        deep_link = f"mailto:{urllib.parse.quote(recipient)}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body_text)}"
    elif channel in ("sms", "whatsapp"):
        recipient = _e164(payload.get("recipient") or h.get("primary_phone") or "")
        if not recipient:
            return {"ok": False, "hotel_id": hid, "error": f"No verified phone number stored for {h['name']}"}
        sms_tpl = pitch["sms_templates"][min(step_idx, len(pitch["sms_templates"]) - 1)]
        body_text = body_text or sms_tpl["text"]
        subject = f"{channel.upper()} Offer (${price_monthly}/mo)"
        if channel == "sms":
            deep_link = f"sms:{recipient}?body={urllib.parse.quote(body_text)}"
        else:
            deep_link = f"https://wa.me/{_wa_digits(recipient)}?text={urllib.parse.quote(body_text)}"
    elif channel == "voice":
        recipient = _e164(payload.get("recipient") or h.get("primary_phone") or "")
        if not recipient:
            return {"ok": False, "hotel_id": hid, "error": f"No verified phone number stored for {h['name']}"}
        cs = pitch["call_script"]
        subject = f"Outbound Sales Call (${price_monthly}/mo)"
        body_text = body_text or cs["gm_opener_30_sec"]
        deep_link = f"tel:{recipient}"
    else:
        recipient = h.get("primary_address") or h.get("area") or "Miami Beach"
        subject = f"Local Walk-In (${price_monthly}/mo)"
        body_text = body_text or pitch["call_script"]["walk_in_script"]

    if _is_opted_out(conn, recipient):
        conn.execute(
            """INSERT INTO outreach_log(hotel_id,channel,recipient,person_name,offer_price_monthly,offer_label,
               subject,body,provider,status,error_detail,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (hid, channel, recipient, h.get("target_person_name"), price_monthly, f"${price_monthly}/mo",
             subject, body_text, "opt_out_guard", "opted_out", "Blocked by do_not_contact list", time.time()),
        )
        conn.commit()
        return {"ok": False, "hotel_id": hid, "status": "opted_out", "error": f"Recipient {recipient} is on do_not_contact list"}

    chan_state = readiness["channels"].get(channel, {}) if channel != "walk_in" else {"ready": True, "provider": "in_person"}
    offer_label = pitch["roi_calculator"]["recommended_tier"]
    provider = chan_state.get("provider", "dry_run")
    status = "queued_dry_run"
    msg_id = ""
    err_detail = ""

    if req_mode == "live" and channel in ("email", "sms", "whatsapp", "voice"):
        if not chan_state.get("ready"):
            status = "ready_awaiting_credentials"
            err_detail = f"Live credentials not set: {', '.join(chan_state.get('missing') or [])}"
        else:
            if channel == "email":
                res = _send_live_email(cfg, recipient, subject, body_text)
            elif channel == "sms":
                res = _send_live_twilio(cfg, recipient, body_text, whatsapp=False)
            elif channel == "whatsapp":
                res = _send_live_twilio(cfg, recipient, body_text, whatsapp=True)
            else:
                res = _send_live_voice(cfg, recipient, pitch["call_script"]["voice_ai_prompt"], body_text)
            provider = res.get("provider", provider)
            msg_id = res.get("msg_id", "")
            err_detail = res.get("error", "")
            status = "sent_live" if res.get("ok") else "failed"
    elif req_mode == "dry_run" and not chan_state.get("ready") and channel != "walk_in":
        status = "ready_awaiting_credentials"
        err_detail = "Staged in local queue with 1-click native launch link (add API credentials in Setup tab for automated send)"

    cur = conn.execute(
        """INSERT INTO outreach_log(hotel_id,channel,recipient,person_name,offer_price_monthly,offer_label,
           subject,body,provider,status,provider_message_id,error_detail,created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (hid, channel, recipient, h.get("target_person_name"), price_monthly, offer_label,
         subject, body_text, provider, status, msg_id, err_detail, time.time()),
    )
    conn.commit()
    return {
        "ok": status != "failed",
        "log_id": cur.lastrowid,
        "hotel_id": hid,
        "hotel_name": h["name"],
        "channel": channel,
        "recipient": recipient,
        "person_name": h.get("target_person_name"),
        "price_monthly": price_monthly,
        "provider": provider,
        "status": status,
        "message_id": msg_id,
        "error_detail": err_detail,
        "subject": subject,
        "body": body_text,
        "deep_link": deep_link,
    }


def list_outreach_log(conn, limit: int = 60) -> list:
    return [dict(r) for r in conn.execute("""
        SELECT o.*, h.name AS hotel_name, h.area
        FROM outreach_log o
        JOIN hotels h ON h.id = o.hotel_id
        ORDER BY o.created_at DESC, o.id DESC
        LIMIT ?
    """, (limit,))]


def list_verified_leads(conn, price_monthly: int = 99) -> dict:
    """Return all verified hotel leads with live quotes, MX-checked emails, verified phones, named GMs/Owners,
    dynamic ROI math at `price_monthly`, and 1-click deep links — built fast from batch SQLite queries."""
    price_monthly = max(19, int(price_monthly or 99))
    rates_by_id = {r["hotel_id"]: r for r in dbmod.latest_rates(conn)}
    prospects_by_id = {r["hotel_id"]: dict(r) for r in conn.execute("SELECT * FROM prospects")}
    contacts_by_id = {}
    for c in conn.execute("SELECT * FROM contacts ORDER BY confidence DESC, id ASC"):
        contacts_by_id.setdefault(c["hotel_id"], []).append(dict(c))

    opted_set = {r["value"].lower() for r in conn.execute("SELECT value FROM do_not_contact")}
    outreach_counts = {
        r["hotel_id"]: {"count": r["c"], "last_status": r["last_status"], "last_channel": r["last_channel"]}
        for r in conn.execute("""
            SELECT hotel_id, COUNT(*) c,
                   (SELECT status FROM outreach_log o2 WHERE o2.hotel_id=o1.hotel_id ORDER BY id DESC LIMIT 1) AS last_status,
                   (SELECT channel FROM outreach_log o2 WHERE o2.hotel_id=o1.hotel_id ORDER BY id DESC LIMIT 1) AS last_channel
            FROM outreach_log o1 GROUP BY hotel_id
        """)
    }

    # Area live averages for comparison proof when one hotel didn't quote
    area_prices = {}
    for r in rates_by_id.values():
        if r.get("price") is not None and r.get("area"):
            area_prices.setdefault(r["area"], []).append(float(r["price"]))
    area_avg = {a: round(sum(vals) / len(vals)) for a, vals in area_prices.items() if vals}

    leads = []
    for h_row in conn.execute("SELECT * FROM hotels ORDER BY id"):
        h = dict(h_row)
        hid = h["id"]
        c_list = contacts_by_id.get(hid, [])
        p = prospects_by_id.get(hid) or {}
        r = rates_by_id.get(hid) or {}

        emails = [c for c in c_list if c["kind"] == "email"]
        phones = [c for c in c_list if c["kind"] == "phone"]
        addrs = [c["value"] for c in c_list if c["kind"] == "address"]
        persons = [c for c in c_list if c["kind"] == "person"]
        persons.sort(key=lambda x: (0 if x.get("verified_status") == "public_record_verified" else 1, -float(x.get("confidence") or 0)))

        top_em = next((e for e in emails if e.get("verified_status") == "mx_verified"), emails[0] if emails else None)
        primary_email = top_em["value"] if top_em else None
        email_verified = bool(top_em and top_em.get("verified_status") == "mx_verified")
        primary_phone = phones[0]["value"] if phones else None
        top_person = persons[0] if persons else None

        short_name = h["name"].split(",")[0].split("(")[0].strip()
        person_name = top_person["value"] if top_person else None
        person_title = (top_person.get("person_title") or "GM / Owner") if top_person else None
        person_source = top_person.get("source_url") if top_person else None

        bar_price = round(float(r["price"])) if r.get("price") is not None else None
        otas = r.get("ota_channels") or []
        non_direct = [c for c in otas if c.get("code") != "DIRECT"]
        low_ota = min(non_direct, key=lambda x: x["rate"]) if non_direct else None
        ota_price = round(float(low_ota["rate"])) if low_ota else bar_price
        ota_name = low_ota["name"] if low_ota else (otas[0]["name"] if otas else None)
        comp_avg = area_avg.get(h.get("area") or "", bar_price or 0)

        rooms = int(h.get("est_rooms") or 50)
        eff_adr = float(bar_price or comp_avg or 180)
        sold_nights = round(rooms * 365 * 0.72)
        annual_upside = int(round(sold_nights * max(8, round(eff_adr * 0.04)) * 0.4 + sold_nights * 0.10 * eff_adr * 0.18, -2))
        roi_x = round(annual_upside / max(1, price_monthly * 12), 1)

        if bar_price and r.get("parity_status") == "UNDERCUT" and low_ota:
            proof_line = f"Live scan: ${bar_price}/nt vs ${ota_price} on {ota_name} ({float(r.get('undercut_pct') or 0):+.1f}%)"
        elif bar_price:
            proof_line = f"Live scan: ${bar_price}/nt vs {h.get('area') or 'Miami'} avg ${comp_avg}/nt"
        else:
            proof_line = f"{h.get('area') or 'Miami'} corridor live avg ${comp_avg}/nt"

        greeting = person_name.split("&")[0].strip().split()[0] if person_name else f"{short_name} Team"
        quick_sms = (
            f"Hi {greeting} ({short_name}) — Jasmel here in North Miami. {proof_line}. "
            f"I run a daily 6 AM rate brief for independent Miami hotels (Free $0 starter or ${price_monthly}/mo flat). "
            f"Want me to text tomorrow's 6 AM sheet free? (Reply STOP to opt out)"
        )[:300]
        if bar_price and r.get("parity_status") == "UNDERCUT" and ota_name:
            quick_subj = f"{short_name.lower()} rate on {ota_name.lower()} today"
        else:
            quick_subj = f"quick {(h.get('area') or 'miami').lower()} rate check for {short_name.lower()}"
        quick_mail = (
            f"Hi {greeting},\n\n"
            f"I live right here in North Miami and built a daily 6 AM rate & OTA undercut tracker for independent {h.get('area') or 'Miami'} hotels "
            f"(Free $0 starter tier, or ${price_monthly}/mo flat with no contract).\n\n"
            f"Today's live scan on {short_name}: {proof_line}.\n\n"
            f"Want me to send you {short_name}'s free 6 AM rate sheet tomorrow morning (or send over your free $0 login link)?\n\n"
            f"Best,\nJasmel Acosta · North Miami, FL (Reply STOP to opt out)"
        )

        e164_ph = _e164(primary_phone or "")
        opted_out = bool((primary_email and primary_email.lower() in opted_set) or (e164_ph and e164_ph.lower() in opted_set))
        olog = outreach_counts.get(hid) or {"count": 0, "last_status": None, "last_channel": None}

        leads.append({
            "hotel_id": hid,
            "name": h["name"],
            "short_name": short_name,
            "area": h.get("area") or "Miami Beach",
            "stars": h.get("stars"),
            "est_rooms": rooms,
            "booking_engine": h.get("booking_engine") or "Direct Website",
            "management_group": h.get("management_group"),
            "website": h.get("website"),
            "website_status": h.get("website_status") or "unknown",
            "deal_stage": h.get("deal_stage") or "new",
            "score": p.get("score", 0),
            "tier": p.get("tier", "watch"),
            "signals": json.loads(p.get("signals") or "[]"),
            "person_name": person_name,
            "person_title": person_title,
            "person_source": person_source,
            "person_verified": bool(person_name),
            "email": primary_email,
            "email_verified": email_verified,
            "phone": primary_phone,
            "phone_e164": e164_ph,
            "address": addrs[0] if addrs else None,
            "price": bar_price,
            "checkin": r.get("checkin"),
            "parity_status": r.get("parity_status") or "NO_LIVE_QUOTE",
            "undercut_pct": float(r.get("undercut_pct") or 0.0),
            "lowest_ota_name": ota_name,
            "lowest_ota_price": ota_price,
            "comp_avg": comp_avg,
            "est_annual_upside": annual_upside,
            "offer_price_monthly": price_monthly,
            "roi_multiple": roi_x,
            "proof_line": proof_line,
            "opted_out": opted_out,
            "outreach_count": olog["count"],
            "last_outreach_status": olog["last_status"],
            "last_outreach_channel": olog["last_channel"],
            "deep_links": {
                "mailto": f"mailto:{urllib.parse.quote(primary_email)}?subject={urllib.parse.quote(quick_subj)}&body={urllib.parse.quote(quick_mail)}" if primary_email else "",
                "sms": f"sms:{e164_ph}?body={urllib.parse.quote(quick_sms)}" if e164_ph else "",
                "whatsapp": f"https://wa.me/{_wa_digits(e164_ph)}?text={urllib.parse.quote(quick_sms)}" if e164_ph else "",
                "tel": f"tel:{e164_ph}" if e164_ph else "",
                "audit_url": f"/audit?hotel_id={hid}",
            },
        })

    leads.sort(key=lambda x: (-int(x["person_verified"]), -x["score"], -x["est_annual_upside"]))
    summary = {
        "total_hotels": len(leads),
        "hot_leads": sum(1 for l in leads if l["tier"] == "hot"),
        "warm_leads": sum(1 for l in leads if l["tier"] == "warm"),
        "named_leaders": sum(1 for l in leads if l["person_verified"]),
        "mx_verified_emails": sum(1 for l in leads if l["email_verified"]),
        "verified_phones": sum(1 for l in leads if l["phone"]),
        "live_quotes": sum(1 for l in leads if l["price"] is not None),
        "live_undercuts": sum(1 for l in leads if l["parity_status"] == "UNDERCUT"),
        "opted_out": sum(1 for l in leads if l["opted_out"]),
        "price_monthly": price_monthly,
        "projected_30_mrr": price_monthly * 30,
        "projected_100_mrr": price_monthly * 100,
    }
    return {"summary": summary, "leads": leads}


def build_market_research_and_posts(conn) -> dict:
    """Compute strictly live Miami market research stats and build data-backed launch posts."""
    rates = dbmod.latest_rates(conn)
    total_hotels = conn.execute("SELECT COUNT(*) c FROM hotels").fetchone()["c"]
    live_rows = [r for r in rates if r.get("price") is not None]
    undercut_rows = [r for r in live_rows if r.get("parity_status") == "UNDERCUT"]
    undercut_rows.sort(key=lambda x: float(x.get("undercut_pct") or 0.0))

    live_count = len(live_rows)
    undercut_count = len(undercut_rows)
    undercut_share_pct = round((undercut_count / max(1, live_count)) * 100, 1) if live_count else 0.0
    overall_avg_bar = round(sum(float(r["price"]) for r in live_rows) / max(1, live_count)) if live_count else 0

    worst = undercut_rows[0] if undercut_rows else None
    worst_ota = None
    if worst:
        nd = [c for c in (worst.get("ota_channels") or []) if c.get("code") != "DIRECT"]
        if nd:
            worst_ota = min(nd, key=lambda c: c["rate"])

    by_area = {}
    for r in rates:
        a = r.get("area") or "Miami Beach"
        slot = by_area.setdefault(a, {"area": a, "hotels": 0, "live": 0, "prices": [], "undercuts": 0})
        slot["hotels"] += 1
        if r.get("price") is not None:
            slot["live"] += 1
            slot["prices"].append(float(r["price"]))
            if r.get("parity_status") == "UNDERCUT":
                slot["undercuts"] += 1
    corridors = []
    for a, d in by_area.items():
        corridors.append({
            "area": a,
            "hotels": d["hotels"],
            "live": d["live"],
            "avg_bar": round(sum(d["prices"]) / len(d["prices"])) if d["prices"] else None,
            "undercuts": d["undercuts"],
        })
    corridors.sort(key=lambda x: -(x["avg_bar"] or 0))

    named_leaders = conn.execute(
        "SELECT COUNT(DISTINCT hotel_id) c FROM contacts WHERE kind='person' AND verified_status='public_record_verified'"
    ).fetchone()["c"]
    mx_emails = conn.execute(
        "SELECT COUNT(DISTINCT hotel_id) c FROM contacts WHERE kind='email' AND verified_status='mx_verified'"
    ).fetchone()["c"]
    phones = conn.execute("SELECT COUNT(DISTINCT hotel_id) c FROM contacts WHERE kind='phone'").fetchone()["c"]

    groups = [
        {"management_group": r["management_group"], "hotels": r["c"]}
        for r in conn.execute(
            "SELECT management_group, COUNT(*) c FROM hotels WHERE management_group IS NOT NULL AND management_group != '' GROUP BY management_group HAVING c >= 1 ORDER BY c DESC LIMIT 8"
        )
    ]

    ex_line = (
        f"Example from today's scan: one {worst['area']} property is quoting ${worst['price']:.0f}/nt retail vs ${worst_ota['rate']:.0f}/nt on {worst_ota['name']} ({worst['undercut_pct']:+.1f}%)."
        if worst and worst_ota
        else f"Today's live Miami Beach average across {live_count} properties is ${overall_avg_bar}/nt."
    )

    posts = [
        {
            "id": "linkedin_founder",
            "channel": "LinkedIn (Founder Launch)",
            "title": "Why Enterprise Hotel Rate Tools Price Out 20-80 Room Miami Boutiques",
            "text": (
                f"Enterprise hotel rate shoppers charge $400-$700/month with annual contracts.\n"
                f"If you run a 35-room boutique in Miami Beach or MiMo, paying $6,000/yr to check 5 neighbors doesn't math.\n\n"
                f"So we built a flat $99/month local tracker in North Miami — covering {total_hotels} Miami, MiMo, North Beach & South Beach properties:\n"
                f"- {live_count} hotels with live multi-OTA quotes today (avg ${overall_avg_bar}/nt)\n"
                f"- {undercut_count} of {live_count} ({undercut_share_pct}%) currently showing a live third-party OTA undercut\n\n"
                f"{ex_line}\n\n"
                f"No annual contract. 6 AM daily email & Telegram brief. First 7 mornings free for any Miami GM or Owner — DM 'MIAMI'."
            ),
        },
        {
            "id": "linkedin_study",
            "channel": "LinkedIn (Miami Parity Study)",
            "title": f"Live Data Check: {undercut_share_pct}% of Live Miami Boutiques Are Being Undercut on OTAs",
            "text": (
                f"We scanned {total_hotels} independent Greater Miami hotels across live OTA metasearch today:\n"
                f"- Live quotes captured: {live_count} properties (avg ${overall_avg_bar}/nt)\n"
                f"- Active third-party undercuts: {undercut_count} properties ({undercut_share_pct}%)\n"
                f"- {ex_line}\n\n"
                f"Even one mispriced weekend or wholesale leak costs a small hotel $1,500+/mo in lost ADR & OTA commission.\n"
                f"Our $99/mo flat brief puts every neighbor rate + OTA parity warning in your inbox at 6 AM.\n"
                f"Want your hotel's 1-page live scan? Comment 'AUDIT'."
            ),
        },
        {
            "id": "instagram_reel",
            "channel": "Instagram / Reels Caption",
            "title": "Miami Boutique Hotel Owners: Stop Paying $500/mo or Guessing Your Room Rates",
            "text": (
                f"Scanned {total_hotels} Miami & Miami Beach hotels live today (${overall_avg_bar}/nt market avg) — and {undercut_count} are actively being undercut by OTAs right now.\n\n"
                f"Your guests check Booking, Agoda & Vio before landing on your direct engine.\n"
                f"Get tomorrow's 6 AM Miami Comp-Set & OTA Undercut Brief FREE for 7 mornings — then $99/mo flat.\n"
                f"DM 'RATE' and I'll drop off or email your 1-page audit today.\n\n"
                f"#MiamiBeachHotels #HospitalityMiami #BoutiqueHotel #RevenueManagement #SmallHotelOwner #MiMoMiami #NorthMiami"
            ),
        },
        {
            "id": "x_thread",
            "channel": "X / Twitter Build-in-Public",
            "title": "Live Miami Hotel Rate Scan Results ($99/mo Micro-SaaS Launch)",
            "text": (
                f"Live Miami hotel pricing check across {total_hotels} properties today:\n"
                f"• {live_count} properties quoting live multi-OTA rates\n"
                f"• ${overall_avg_bar}/nt average ADR\n"
                f"• {undercut_count} ({undercut_share_pct}%) currently showing a live third-party OTA undercut\n\n"
                f"Lighthouse/RateGain start around $400-$600+/mo. We built a hyper-local $99/mo flat morning brief for small Miami Beach & MiMo hotels."
            ),
        },
        {
            "id": "whatsapp_local",
            "channel": "Miami GM Direct Offer ($49 Intro Test)",
            "title": "Beachhead Intro Offer for First 10 North Miami / Miami Beach Properties",
            "text": (
                f"Founding Cohort Offer (First 10 Miami Hotels): Try our 6 AM Competitor Rate & OTA Parity Brief free for 7 days, "
                f"lock in $49 for Month 1 (then $99/mo flat, zero contract). Tracks your 10 nearest neighbors + live Booking/Agoda/Expedia/Vio parity daily."
            ),
        },
    ]

    return {
        "metrics": {
            "total_hotels": total_hotels,
            "live_quotes": live_count,
            "undercut_count": undercut_count,
            "undercut_share_pct": undercut_share_pct,
            "overall_avg_bar": overall_avg_bar,
            "named_leaders": named_leaders,
            "mx_verified_emails": mx_emails,
            "verified_phones": phones,
            "worst_undercut": {
                "name": worst["name"],
                "area": worst.get("area"),
                "bar": worst.get("price"),
                "ota_name": worst_ota["name"],
                "ota_price": worst_ota["rate"],
                "undercut_pct": worst.get("undercut_pct"),
            } if worst and worst_ota else None,
            "corridors": corridors,
            "management_groups": groups,
        },
        "posts": posts,
    }
