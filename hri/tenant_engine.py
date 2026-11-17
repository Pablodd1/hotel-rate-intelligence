"""Multi-Tenant Client Account Isolation, Tier Ladder (Free -> $99 -> $199 -> $399),
Admin Mission Control Auth, and Marketing Campaign Approval Engine.

Strict Separation of 3 Portals:
  1. Public Website (`/` or `/website`)      — Instagram Reel UI Website Recreation style, features,
                                               why us vs others, labor/hours/money ROI calculator,
                                               Free -> $99 -> $199 tier comparison, 1-click Demo Client #1,
                                               and self-serve hotel registration.
  2. Hotel Client Portal (`/portal`)         — Independent per-hotel login & password. Strictly isolated
                                               to ONLY that account's primary hotel + assigned comp-set.
                                               Cannot see other client accounts, Mission Control, or the
                                               global 49-hotel lead database.
  3. Admin Mission Control (`/mission-control`) — Protected by Owner Login & Password (jasmel / admin305).
                                               Oversees all 49 Miami leads, approves/dispatches marketing
                                               campaigns, manages all hotel client accounts & comp-set
                                               assignments, compares tiers, and controls global scraping.
"""
import hashlib
import json
import secrets
import time
from datetime import date, timedelta

from . import db as dbmod
from .memory_engine import estimate_occupancy_and_personality, record_and_analyze_memory
from .call_assistant import COURTESY_CALL_TEMPLATES, place_or_log_courtesy_call
from .sales_engine import build_comp_set_svg, build_hotel_pitch, build_ota_ladder_svg, MIAMI_COMPRESSION_EVENTS
from .outreach_engine import send_or_queue_outreach, list_verified_leads, list_outreach_log, get_channel_readiness, build_market_research_and_posts


# Ordered starting with FREE ($0/mo) -> Core ($99/mo) -> Pro ($199/mo) -> Portfolio ($399/mo)
TIER_CATALOG = [
    {
        "tier_id": "free",
        "name": "Tier 1 · Free Starter",
        "badge": "START FREE · $0/MO",
        "monthly_price": 0,
        "intro_price": 0,
        "max_competitors": 3,
        "allow_live_scrape": True,
        "allow_daily_email_telegram": False,
        "allow_memory_engine": True,
        "allow_courtesy_calls": False,
        "allow_instant_sms_alerts": False,
        "allow_custom_tags": True,
        "staff_hours_saved_mo": 15,
        "labor_dollars_saved_mo": 375,
        "est_revenue_recovered_mo": 950,
        "headline": "See Your Hotel vs. 3 Assigned Neighbors + Live Scraping Demo",
        "who_for": "New hotel registrants testing live Xotelo + direct website rate comparison with zero risk.",
        "features": [
            "Isolated Hotel Account with private login & password",
            "Your Hotel + up to 3 assigned neighbor competitors",
            "Live BAR & multi-OTA parity check (Booking, Expedia, Agoda)",
            "Sample Competitor Pricing Memory & strategy tags",
            "Saves ~15 hrs/mo of manual front-desk OTA tab checking",
        ],
        "locked_features": [
            "Full 10-hotel corridor comp-set scraping (Unlocks in Core $99)",
            "Automated 6:00 AM Daily Email & Telegram Strategy Brief (Unlocks in Core $99)",
            "Overnight Courtesy Call-Around Occupancy Desk (Unlocks in Pro $199)",
            "Instant SMS/WhatsApp wholesale undercut alerts (Unlocks in Pro $199)",
        ],
    },
    {
        "tier_id": "core_99",
        "name": "Tier 2 · Boutique Core",
        "badge": "MOST POPULAR · $99/MO ($49 M1)",
        "monthly_price": 99,
        "intro_price": 49,
        "max_competitors": 10,
        "allow_live_scrape": True,
        "allow_daily_email_telegram": True,
        "allow_memory_engine": True,
        "allow_courtesy_calls": False,
        "allow_instant_sms_alerts": False,
        "allow_custom_tags": True,
        "staff_hours_saved_mo": 45,
        "labor_dollars_saved_mo": 1125,
        "est_revenue_recovered_mo": 3400,
        "headline": "Full Corridor Comp-Set + 6 AM Email/Telegram Brief + Rate Memory",
        "who_for": "Independent 15–80 room Miami boutique hotels replacing manual spreadsheets & $500/mo tools.",
        "features": [
            "Everything in Free + up to 10 assigned corridor competitors",
            "On-demand live Xotelo + Direct JSON-LD rate scraping",
            "Automated 6:00 AM Daily Email & Telegram Rate Strategy Brief",
            "Full Multi-OTA Undercut Detector (Agoda, Vio, Booking, Expedia, Trip.com)",
            "Competitor Pricing Memory Engine (memorizes every competitor move)",
            "Actionable HOLD / RAISE / MATCH rate recommendations",
            "Saves ~45 hrs/mo of GM & front-desk labor ($1,125/mo value)",
        ],
        "locked_features": [
            "Overnight Courtesy Call-Around Occupancy Desk (Unlocks in Pro $199)",
            "Instant SMS & WhatsApp OTA undercut alerts (Unlocks in Pro $199)",
        ],
    },
    {
        "tier_id": "pro_199",
        "name": "Tier 3 · Pro Revenue & Call Desk",
        "badge": "FULL AUTOMATION · $199/MO",
        "monthly_price": 199,
        "intro_price": 149,
        "max_competitors": 20,
        "allow_live_scrape": True,
        "allow_daily_email_telegram": True,
        "allow_memory_engine": True,
        "allow_courtesy_calls": True,
        "allow_instant_sms_alerts": True,
        "allow_custom_tags": True,
        "staff_hours_saved_mo": 68,
        "labor_dollars_saved_mo": 1700,
        "est_revenue_recovered_mo": 6200,
        "headline": "Adds Overnight Courtesy Call-Around Occupancy Desk + Instant SMS Alerts",
        "who_for": "High-ADR boutiques ($220+/nt) maximizing occupancy yield and eliminating wholesale leaks.",
        "features": [
            "Everything in Core $99 + up to 20 assigned competitors",
            "Overnight Courtesy Call-Around Occupancy Desk (scripts, logging & AI voice ready)",
            "Instant SMS & WhatsApp alerts when an OTA undercuts your direct BAR",
            "Miami Event & Compression Radar (Art Basel, F1, Boat Show, Hard Rock)",
            "1-Click Printable Executive Revenue Audit Sheets",
            "Saves ~68 hrs/mo across Front Desk, Night Audit & GM ($1,700/mo labor saved)",
        ],
        "locked_features": [],
    },
    {
        "tier_id": "portfolio_399",
        "name": "Tier 4 · Multi-Property Group",
        "badge": "HOTEL GROUPS · $399/MO",
        "monthly_price": 399,
        "intro_price": 299,
        "max_competitors": 49,
        "allow_live_scrape": True,
        "allow_daily_email_telegram": True,
        "allow_memory_engine": True,
        "allow_courtesy_calls": True,
        "allow_instant_sms_alerts": True,
        "allow_custom_tags": True,
        "staff_hours_saved_mo": 140,
        "labor_dollars_saved_mo": 3500,
        "est_revenue_recovered_mo": 14500,
        "headline": "Up to 5 Sister Properties + Corridor-Wide Intelligence + Local Review",
        "who_for": "Miami boutique hospitality groups (2–5 properties) managing cluster yield.",
        "features": [
            "Up to 5 owned properties with isolated or group logins",
            "Full corridor comp-set assignment across all Miami submarkets",
            "Group-wide OTA parity audit & overnight occupancy call desk",
            "Monthly in-person Miami revenue strategy review",
        ],
        "locked_features": [],
    },
]

TIER_BY_ID = {t["tier_id"]: t for t in TIER_CATALOG}

COMPETITOR_COMPARISON_MATRIX = [
    {
        "feature": "Monthly Cost for a 45-Room Boutique",
        "us_free": "$0 / mo (Forever Starter)",
        "us_core": "$99 / mo ($49 Month 1)",
        "us_pro": "$199 / mo",
        "enterprise": "$450 – $750+ / mo",
        "spreadsheets": "$0 software, ~$1,125/mo in staff labor",
    },
    {
        "feature": "Contract Requirement",
        "us_free": "None (Instant Signup)",
        "us_core": "Month-to-Month (Cancel Anytime)",
        "us_pro": "Month-to-Month (Cancel Anytime)",
        "enterprise": "12 to 24-Month Annual Lock-In",
        "spreadsheets": "N/A",
    },
    {
        "feature": "Staff Hours Spent Checking Rates / Mo",
        "us_free": "Saves ~15 hrs/mo",
        "us_core": "Saves ~45 hrs/mo (1.5 hrs/day)",
        "us_pro": "Saves ~68 hrs/mo (2.2 hrs/day)",
        "enterprise": "Requires dedicated Revenue Manager",
        "spreadsheets": "Wastes 45–68 hrs/mo of GM/Front-Desk time",
    },
    {
        "feature": "Isolated Per-Hotel Account & Comp-Set",
        "us_free": "Yes (Your Hotel + 3 Neighbors)",
        "us_core": "Yes (Your Hotel + 10 Competitors)",
        "us_pro": "Yes (Your Hotel + 20 Competitors)",
        "enterprise": "Complex enterprise seat licensing",
        "spreadsheets": "Shared messy tabs, zero history",
    },
    {
        "feature": "Live Multi-OTA Undercut Detection (Agoda, Vio, Booking, Expedia)",
        "us_free": "Basic Parity Badge",
        "us_core": "Full Multi-OTA Channel Breakdown",
        "us_pro": "Full Breakdown + Instant SMS/WA Alert",
        "enterprise": "Paid add-on module (+$150/mo)",
        "spreadsheets": "Spot-checked manually (misses wholesale leaks)",
    },
    {
        "feature": "Competitor Pricing Memory & Decision Logic",
        "us_free": "Preview",
        "us_core": "Included (Tracks every rate move)",
        "us_pro": "Included + Event Compression Radar",
        "enterprise": "Raw charts only — no plain-English action",
        "spreadsheets": "None (yesterday's rates overwritten)",
    },
    {
        "feature": "Overnight Courtesy Call-Around Occupancy Desk",
        "us_free": "Upgrade to Pro",
        "us_core": "Upgrade to Pro",
        "us_pro": "Included (Scripts, Log & Voice AI Ready)",
        "enterprise": "Not available in any legacy tool",
        "spreadsheets": "Paper sticky notes lost at shift change",
    },
]


def _hash_password(password: str) -> str:
    salt = "hri-miami-305-salt"
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 12000)
    return dk.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    if not password or not stored_hash:
        return False
    return _hash_password(password) == stored_hash or password == stored_hash


def verify_admin_credentials(cfg: dict, username: str, password: str) -> dict:
    admin_cfg = cfg.get("admin_auth") or {}
    expected_user = (admin_cfg.get("username") or "jasmel").strip().lower()
    expected_pass = admin_cfg.get("password") or "admin305"
    u_clean = (username or "").strip().lower()
    if u_clean in (expected_user, "admin", "jasmel", "jasmelacosta@gmail.com") and password == expected_pass:
        token = admin_cfg.get("session_token") or "mc-admin-jasmel-305"
        return {
            "ok": True,
            "role": "admin",
            "username": expected_user,
            "owner_name": admin_cfg.get("owner_name") or "Jasmel Acosta",
            "token": token,
        }
    return {"ok": False, "error": "Invalid Administrator username or password."}


def is_admin_token_valid(cfg: dict, token: str) -> bool:
    if not token:
        return False
    expected = (cfg.get("admin_auth") or {}).get("session_token") or "mc-admin-jasmel-305"
    return token.strip() == expected


def _corridor_competitor_ids(conn, primary_hotel_id: int, limit: int = 8) -> list:
    h = conn.execute("SELECT id, area FROM hotels WHERE id=?", (primary_hotel_id,)).fetchone()
    if not h:
        rows = conn.execute("SELECT id FROM hotels ORDER BY id LIMIT ?", (limit + 1,)).fetchall()
        return [r["id"] for r in rows]
    area = h["area"] or "South Beach"
    same_area = [
        r["id"]
        for r in conn.execute(
            """SELECT h.id FROM hotels h
               LEFT JOIN rates rt ON rt.hotel_id = h.id
               WHERE h.area=? AND h.id!=?
               GROUP BY h.id
               ORDER BY COUNT(rt.id) DESC, h.id ASC
               LIMIT ?""",
            (area, primary_hotel_id, limit),
        ).fetchall()
    ]
    ids = [primary_hotel_id] + same_area
    if len(ids) < limit + 1:
        extra = [
            r["id"]
            for r in conn.execute(
                "SELECT id FROM hotels WHERE id NOT IN ({}) ORDER BY id LIMIT ?".format(",".join(map(str, ids))),
                (limit + 1 - len(ids),),
            ).fetchall()
        ]
        ids.extend(extra)
    return ids


def ensure_seed_accounts_and_campaigns(conn, cfg):
    """Idempotently seed Mock Demo Client #1 (`avalon`), Free (`vagabond`), Core (`waterside`),
    sample client tags, and initial pending/approved marketing campaigns for Mission Control.
    """
    existing = conn.execute("SELECT COUNT(*) c FROM client_accounts").fetchone()["c"]
    now = time.time()

    if existing == 0:
        # 1. Mock Demo Client #1: Avalon Hotel South Beach (Pro Tier showcase, with interactive tier preview)
        avalon_row = conn.execute("SELECT id, name, area FROM hotels WHERE name LIKE '%Avalon%' LIMIT 1").fetchone()
        if not avalon_row:
            avalon_row = conn.execute("SELECT id, name, area FROM hotels ORDER BY id LIMIT 1").fetchone()
        avalon_id = avalon_row["id"]
        avalon_comp_ids = _corridor_competitor_ids(conn, avalon_id, limit=8)

        conn.execute(
            """INSERT INTO client_accounts(
                 username, email, password_hash, display_name, contact_person,
                 primary_hotel_id, assigned_hotel_ids, tier, monthly_price,
                 status, is_demo, alert_email, telegram_chat_id, session_token, created_at
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "avalon",
                "demo@avalonhotel.com",
                _hash_password("demo1234"),
                f"{avalon_row['name']} (Demo Client #1)",
                "Front Office & Revenue Team (Mock Demo #1)",
                avalon_id,
                json.dumps(avalon_comp_ids),
                "pro_199",
                199,
                "active",
                1,
                "revenue@avalonhotel.com",
                "@avalon_sobe_rates",
                "client-demo-avalon-token",
                now,
            ),
        )
        avalon_acc_id = conn.execute("SELECT id FROM client_accounts WHERE username='avalon'").fetchone()["id"]

        # Seed realistic strategy tags scoped strictly to Avalon's assigned South Beach comp-set
        tag_seeds = [
            (avalon_comp_ids[0], "OUR PROPERTY · 700 Ocean Dr", "Target 82% occupancy floor before lifting weekend BAR +$18.", "#facc15"),
            (avalon_comp_ids[1] if len(avalon_comp_ids) > 1 else avalon_id, "Direct Ocean Dr Rival", "Matches our weekday BAR within $5; watch Friday 4 PM rate moves.", "#38bdf8"),
            (avalon_comp_ids[2] if len(avalon_comp_ids) > 2 else avalon_id, "OTA Undercut Watch", "Frequently leaks wholesale inventory on Agoda & Vio (-15% to -40%).", "#f87171"),
            (avalon_comp_ids[3] if len(avalon_comp_ids) > 3 else avalon_id, "Call Night Audit 11:45 PM", "Front desk shares exact rooms-left count during overnight courtesy call.", "#34d399"),
        ]
        for hid, tag, note, color in tag_seeds:
            conn.execute(
                "INSERT INTO hotel_tags(account_id, hotel_id, tag, note, color, created_at) VALUES (?,?,?,?,?,?)",
                (avalon_acc_id, hid, tag, note, color, now),
            )

        # 2. Tier 1 Free ($0/mo) Comparison Account: The Vagabond Hotel (MiMo / Biscayne Blvd)
        vag_row = conn.execute("SELECT id, name FROM hotels WHERE name LIKE '%Vagabond%' LIMIT 1").fetchone()
        if vag_row:
            vag_ids = _corridor_competitor_ids(conn, vag_row["id"], limit=3)
            conn.execute(
                """INSERT INTO client_accounts(
                     username, email, password_hash, display_name, contact_person,
                     primary_hotel_id, assigned_hotel_ids, tier, monthly_price,
                     status, is_demo, alert_email, telegram_chat_id, session_token, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "vagabond",
                    "gm@thevagabondhotel.com",
                    _hash_password("demo1234"),
                    f"{vag_row['name']} (Free Tier Sample)",
                    "Avra Jain / Dalia Lagoa",
                    vag_row["id"],
                    json.dumps(vag_ids),
                    "free",
                    0,
                    "active",
                    1,
                    "info@thevagabondhotel.com",
                    "",
                    "client-free-vagabond-token",
                    now,
                ),
            )

        # 3. Tier 2 Core ($99/mo) Comparison Account: Waterside Hotel & Suites (North Beach)
        wat_row = conn.execute("SELECT id, name FROM hotels WHERE name LIKE '%Waterside%' LIMIT 1").fetchone()
        if wat_row:
            wat_ids = _corridor_competitor_ids(conn, wat_row["id"], limit=8)
            conn.execute(
                """INSERT INTO client_accounts(
                     username, email, password_hash, display_name, contact_person,
                     primary_hotel_id, assigned_hotel_ids, tier, monthly_price,
                     status, is_demo, alert_email, telegram_chat_id, session_token, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "waterside",
                    "ops@watersidehotelmiami.com",
                    _hash_password("demo1234"),
                    f"{wat_row['name']} (Core $99 Sample)",
                    "North Beach Operations",
                    wat_row["id"],
                    json.dumps(wat_ids),
                    "core_99",
                    99,
                    "active",
                    1,
                    "ops@watersidehotelmiami.com",
                    "@waterside_nobe",
                    "client-core-waterside-token",
                    now,
                ),
            )
        conn.commit()

    # Seed Marketing Campaigns in Mission Control if empty
    camp_cnt = conn.execute("SELECT COUNT(*) c FROM marketing_campaigns").fetchone()["c"]
    if camp_cnt == 0:
        leads_data = list_verified_leads(conn, price_monthly=99)
        leads = leads_data.get("leads") or []
        seeded = 0
        for ld in leads[:14]:
            hid = ld["hotel_id"]
            hname = ld["name"]
            area = ld["area"]
            person = ld.get("person_name") or f"{hname} GM / Revenue Team"
            reg_url = f"{_base_url(cfg)}/website?hotel_id={hid}#register"
            demo_url = f"{_base_url(cfg)}/portal?demo_hotel={hid}"
            proof = ld.get("proof_line") or f"Live {area} corridor rate scan ready."

            # 1) Email Campaign (Y Combinator 3-Sentence Cold Email Framework:
            #    casual subject line, 3 plain sentences, live proof early, 1-line ask at the bottom, zero meeting push)
            if ld.get("email"):
                short_h = ld.get("short_name") or hname.split(",")[0].strip()
                ota_nm = (ld.get("lowest_ota_name") or "ota").lower()
                if ld.get("parity_status") == "UNDERCUT" and ld.get("price"):
                    subj = f"{short_h.lower()} rate on {ota_nm} today"
                else:
                    subj = f"quick {area.lower()} rate check for {short_h.lower()}"
                first_person = person.split("/")[0].split("(")[0].strip()
                body = (
                    f"Hi {first_person},\n\n"
                    f"I live right here in North Miami and built a daily 6 AM rate & OTA undercut tracker for independent {area} hotels "
                    f"(Free $0 starter tier, or $99/mo flat with no contract).\n\n"
                    f"Today's live scan on {short_h}: {proof} (we already built a private rate panel demo for {short_h} showing neighbor moves so your desk saves ~45 hrs/mo).\n\n"
                    f"Want me to send tomorrow's 6 AM rate sheet for {short_h}, or check your live demo panel at {demo_url} (free claim: {reg_url})?\n\n"
                    f"Best,\nJasmel Acosta\nHotel Rate Intelligence · North Miami, FL 33161 (Reply STOP to opt out)"
                )
                conn.execute(
                    """INSERT INTO marketing_campaigns(
                         hotel_id, campaign_name, channel, target_tier, recipient,
                         person_name, subject, body, registration_url, approval_status, created_at
                       ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        hid,
                        f"YC 3-Sentence · {area} (Free->$99)",
                        "email",
                        "free_to_99",
                        ld["email"],
                        person,
                        subj,
                        body,
                        reg_url,
                        "approved" if seeded < 4 else "pending_approval",
                        now - seeded * 120,
                    ),
                )
                seeded += 1

            # 2) SMS / WhatsApp / Voice Campaign for top undercuts
            if ld.get("phone") and seeded < 18:
                ch = "whatsapp" if (seeded % 3 == 1) else ("sms" if (seeded % 3 == 2) else "voice")
                sms_body = (
                    f"Hi {person.split('/')[0].strip()} ({hname}) — Jasmel here in Miami. "
                    f"{proof} We unlocked a Free ($0) rate-scraper & parity account for {hname} "
                    f"(saves ~45 hrs/mo of staff rate checks; Core tier is just $99/mo flat). "
                    f"Preview live demo: {demo_url} or register {hname}: {reg_url} (Reply STOP to opt out)"
                )
                conn.execute(
                    """INSERT INTO marketing_campaigns(
                         hotel_id, campaign_name, channel, target_tier, recipient,
                         person_name, subject, body, registration_url, approval_status, created_at
                       ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        hid,
                        f"{area} {ch.upper()} Direct Proof + Free Signup",
                        ch,
                        "free_to_99",
                        ld["phone"],
                        person,
                        f"{hname} {ch.upper()} Outreach",
                        sms_body,
                        reg_url,
                        "pending_approval",
                        now - seeded * 90,
                    ),
                )
                seeded += 1
        conn.commit()


def _serialize_account(conn, row) -> dict:
    d = dict(row)
    d.pop("password_hash", None)
    assigned_ids = json.loads(d.get("assigned_hotel_ids") or "[]")
    d["assigned_hotel_ids"] = assigned_ids
    d["tier_meta"] = TIER_BY_ID.get(d.get("tier") or "free", TIER_CATALOG[0])
    h_primary = conn.execute("SELECT id, name, area, stars, est_rooms, website FROM hotels WHERE id=?", (d["primary_hotel_id"],)).fetchone()
    d["primary_hotel"] = dict(h_primary) if h_primary else {"id": d["primary_hotel_id"], "name": d["display_name"], "area": "Miami Beach"}
    if assigned_ids:
        placeholders = ",".join("?" for _ in assigned_ids)
        h_rows = conn.execute(f"SELECT id, name, area, stars, est_rooms FROM hotels WHERE id IN ({placeholders})", assigned_ids).fetchall()
        by_id = {r["id"]: dict(r) for r in h_rows}
        d["assigned_hotels"] = [by_id[i] for i in assigned_ids if i in by_id]
    else:
        d["assigned_hotels"] = []
    d["assigned_count"] = len(d["assigned_hotels"])
    return d


def _base_url(cfg: dict = None) -> str:
    base = ((cfg or {}).get("outreach") or {}).get("app_base_url") or "http://127.0.0.1:8317"
    return str(base).rstrip("/")


def list_client_accounts(conn) -> list:
    rows = conn.execute("SELECT * FROM client_accounts ORDER BY is_demo DESC, id ASC").fetchall()
    return [_serialize_account(conn, r) for r in rows]


def get_or_create_demo_account_for_hotel(conn, cfg: dict, hotel_id: int) -> dict:
    """Instant personalized Panel Demo (`/portal?demo_hotel=<ID>`) for any of the verified hotels.
    Produces an isolated sandbox scoped exclusively to that hotel and its nearest corridor neighbors.
    """
    hid = int(hotel_id or 1)
    h_row = conn.execute("SELECT * FROM hotels WHERE id=?", (hid,)).fetchone()
    if not h_row:
        h_row = conn.execute("SELECT * FROM hotels ORDER BY id LIMIT 1").fetchone()
    if not h_row:
        return {"ok": False, "error": "Hotel not found"}
    hid = int(h_row["id"])
    uname = f"demo_h{hid}"
    existing = conn.execute("SELECT * FROM client_accounts WHERE username=?", (uname,)).fetchone()
    if existing:
        conn.execute("UPDATE client_accounts SET last_login_at=? WHERE id=?", (time.time(), existing["id"]))
        conn.commit()
        return {"ok": True, "account": _serialize_account(conn, existing), "token": existing["session_token"]}

    comp_ids = _corridor_competitor_ids(conn, hid, limit=8)
    now = time.time()
    token = f"client-demo-hotel-{hid}"
    person_row = conn.execute("SELECT value FROM contacts WHERE hotel_id=? AND kind='person' LIMIT 1", (hid,)).fetchone()
    person_lbl = person_row["value"] if person_row else f"{h_row['name']} GM / Revenue Team"
    email_row = conn.execute("SELECT value FROM contacts WHERE hotel_id=? AND kind='email' LIMIT 1", (hid,)).fetchone()
    email_lbl = email_row["value"] if email_row else f"demo-h{hid}@miamihotelintel.local"
    conn.execute(
        """INSERT INTO client_accounts(
             username, email, password_hash, display_name, contact_person,
             primary_hotel_id, assigned_hotel_ids, tier, monthly_price,
             status, is_demo, alert_email, telegram_chat_id, session_token, last_login_at, created_at
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            uname,
            email_lbl,
            _hash_password("demo1234"),
            f"{h_row['name']} (Personal Panel Demo)",
            person_lbl,
            hid,
            json.dumps(comp_ids),
            "pro_199",
            199,
            "active",
            1,
            email_lbl,
            "",
            token,
            now,
            now,
        ),
    )
    acc_id = conn.execute("SELECT id FROM client_accounts WHERE username=?", (uname,)).fetchone()["id"]
    tag_seeds = [
        (comp_ids[0], "MY HOTEL PROPERTY", f"Isolated preview for {h_row['name']} — compare Free ($0) vs Core ($99) vs Pro ($199).", "#facc15"),
    ]
    if len(comp_ids) > 1:
        tag_seeds.append((comp_ids[1], "Closest Corridor Rival", "Track weekend BAR & live OTA undercut shifts here.", "#38bdf8"))
    for thid, tlabel, tnote, tcol in tag_seeds:
        conn.execute(
            "INSERT INTO hotel_tags(account_id, hotel_id, tag, note, color, created_at) VALUES (?,?,?,?,?,?)",
            (acc_id, thid, tlabel, tnote, tcol, now),
        )
    conn.commit()
    created = conn.execute("SELECT * FROM client_accounts WHERE id=?", (acc_id,)).fetchone()
    return {"ok": True, "account": _serialize_account(conn, created), "token": token}


def authenticate_client(conn, username_or_email: str, password: str, demo_fallback: bool = False, demo_hotel_id: int = None) -> dict:
    if demo_hotel_id:
        return get_or_create_demo_account_for_hotel(conn, {}, int(demo_hotel_id))
    if demo_fallback and not username_or_email:
        row = conn.execute("SELECT * FROM client_accounts WHERE username='avalon' OR is_demo=1 ORDER BY id ASC LIMIT 1").fetchone()
        if row:
            conn.execute("UPDATE client_accounts SET last_login_at=? WHERE id=?", (time.time(), row["id"]))
            conn.commit()
            return {"ok": True, "account": _serialize_account(conn, row), "token": row["session_token"]}

    u = (username_or_email or "").strip().lower()
    row = conn.execute(
        "SELECT * FROM client_accounts WHERE LOWER(username)=? OR LOWER(email)=? LIMIT 1",
        (u, u),
    ).fetchone()
    if not row:
        return {"ok": False, "error": "Hotel account not found. Check your username/email or register a Free Hotel Account."}
    if not verify_password(password, row["password_hash"]):
        return {"ok": False, "error": "Invalid password for this hotel account."}
    if row["status"] == "suspended":
        return {"ok": False, "error": "This hotel account is currently suspended. Contact Mission Control."}
    token = row["session_token"] or f"client-{row['username']}-{secrets.token_hex(6)}"
    conn.execute("UPDATE client_accounts SET session_token=?, last_login_at=? WHERE id=?", (token, time.time(), row["id"]))
    conn.commit()
    row = conn.execute("SELECT * FROM client_accounts WHERE id=?", (row["id"],)).fetchone()
    return {"ok": True, "account": _serialize_account(conn, row), "token": token}


def get_client_by_token(conn, token: str):
    if not token:
        return None
    row = conn.execute("SELECT * FROM client_accounts WHERE session_token=? LIMIT 1", (token.strip(),)).fetchone()
    return _serialize_account(conn, row) if row else None


def register_or_create_client_account(conn, payload: dict, created_by_admin: bool = False) -> dict:
    """Self-serve registration from Public Website OR Admin creation from Mission Control."""
    hotel_id = payload.get("primary_hotel_id") or payload.get("hotel_id")
    hotel_name = (payload.get("hotel_name") or "").strip()
    area = (payload.get("area") or "South Beach").strip()

    if hotel_id:
        h_row = conn.execute("SELECT * FROM hotels WHERE id=?", (int(hotel_id),)).fetchone()
    elif hotel_name:
        h_row = conn.execute("SELECT * FROM hotels WHERE LOWER(name)=LOWER(?) LIMIT 1", (hotel_name,)).fetchone()
    else:
        h_row = None

    if not h_row:
        if not hotel_name:
            return {"ok": False, "error": "Please select your hotel or enter your hotel name."}
        hid = dbmod.upsert_hotel(
            conn,
            name=hotel_name,
            area=area,
            website=payload.get("website") or "",
            stars=float(payload.get("stars") or 3.5),
            est_rooms=int(payload.get("est_rooms") or 42),
            booking_engine="Direct Website",
            price_min=150.0,
            price_max=330.0,
        )
        h_row = conn.execute("SELECT * FROM hotels WHERE id=?", (hid,)).fetchone()

    primary_hid = int(h_row["id"])
    tier = (payload.get("tier") or "free").strip().lower()
    if tier not in TIER_BY_ID:
        tier = "free"
    tier_meta = TIER_BY_ID[tier]

    raw_user = (payload.get("username") or "").strip().lower()
    email = (payload.get("email") or "").strip().lower()
    if not raw_user:
        base_slug = "".join(ch for ch in h_row["name"].lower() if ch.isalnum())[:14] or f"hotel{primary_hid}"
        raw_user = base_slug
    # Ensure username uniqueness
    candidate = raw_user
    suffix = 1
    while conn.execute("SELECT 1 FROM client_accounts WHERE LOWER(username)=?", (candidate,)).fetchone():
        if created_by_admin and payload.get("overwrite_existing"):
            break
        suffix += 1
        candidate = f"{raw_user}{suffix}"
    username = candidate

    password = (payload.get("password") or "hotel305").strip()
    if len(password) < 4:
        return {"ok": False, "error": "Password must be at least 4 characters."}

    # Determine assigned competitor hotels (strictly scoped to this account)
    explicit_ids = payload.get("assigned_hotel_ids")
    if isinstance(explicit_ids, list) and explicit_ids:
        assigned_ids = [int(x) for x in explicit_ids if str(x).isdigit()]
        if primary_hid not in assigned_ids:
            assigned_ids.insert(0, primary_hid)
    else:
        max_comp = int(tier_meta.get("max_competitors") or 3)
        assigned_ids = _corridor_competitor_ids(conn, primary_hid, limit=max_comp)

    token = f"client-{username}-{secrets.token_hex(6)}"
    now = time.time()
    contact_person = (payload.get("contact_person") or payload.get("person_name") or "Hotel GM / Revenue Team").strip()
    display_name = payload.get("display_name") or h_row["name"]

    conn.execute(
        """INSERT INTO client_accounts(
             username, email, password_hash, display_name, contact_person,
             primary_hotel_id, assigned_hotel_ids, tier, monthly_price,
             status, is_demo, alert_email, telegram_chat_id, session_token, last_login_at, created_at
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            username,
            email or f"{username}@hotelclient.com",
            _hash_password(password),
            display_name,
            contact_person,
            primary_hid,
            json.dumps(assigned_ids),
            tier,
            int(tier_meta["monthly_price"]),
            "active",
            int(bool(payload.get("is_demo"))),
            email or f"{username}@hotelclient.com",
            (payload.get("telegram_chat_id") or "").strip(),
            token,
            now,
            now,
        ),
    )
    acc_id = conn.execute("SELECT id FROM client_accounts WHERE username=?", (username,)).fetchone()["id"]
    conn.execute("UPDATE hotels SET deal_stage='registered_client' WHERE id=?", (primary_hid,))
    conn.execute(
        "INSERT INTO hotel_tags(account_id, hotel_id, tag, note, color, created_at) VALUES (?,?,?,?,?,?)",
        (acc_id, primary_hid, "MY HOTEL PROPERTY", f"Isolated {tier_meta['name']} account for {h_row['name']}", "#facc15", now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM client_accounts WHERE id=?", (acc_id,)).fetchone()
    return {
        "ok": True,
        "account": _serialize_account(conn, row),
        "token": token,
        "portal_url": f"/portal?token={token}",
    }


def update_client_account_admin(conn, payload: dict) -> dict:
    """Mission Control admin endpoint to update a client's tier, assigned comp-set, or credentials."""
    acc_id = int(payload.get("account_id") or payload.get("id") or 0)
    row = conn.execute("SELECT * FROM client_accounts WHERE id=?", (acc_id,)).fetchone()
    if not row:
        return {"ok": False, "error": "Client account not found"}

    tier = (payload.get("tier") or row["tier"]).strip().lower()
    if tier not in TIER_BY_ID:
        tier = row["tier"]
    tier_meta = TIER_BY_ID[tier]
    monthly_price = int(payload.get("monthly_price") if payload.get("monthly_price") is not None else tier_meta["monthly_price"])

    primary_hid = int(payload.get("primary_hotel_id") or row["primary_hotel_id"])
    if isinstance(payload.get("assigned_hotel_ids"), list):
        assigned_ids = [int(x) for x in payload["assigned_hotel_ids"] if str(x).isdigit()]
        if primary_hid not in assigned_ids:
            assigned_ids.insert(0, primary_hid)
    else:
        assigned_ids = json.loads(row["assigned_hotel_ids"] or "[]")
        if primary_hid not in assigned_ids:
            assigned_ids.insert(0, primary_hid)

    new_pass = (payload.get("password") or "").strip()
    pass_hash = _hash_password(new_pass) if new_pass else row["password_hash"]
    status = (payload.get("status") or row["status"]).strip()
    display_name = (payload.get("display_name") or row["display_name"]).strip()
    contact_person = (payload.get("contact_person") or row["contact_person"] or "").strip()
    email = (payload.get("email") or row["email"]).strip()
    alert_email = (payload.get("alert_email") or row["alert_email"] or email).strip()
    tg_chat = (payload.get("telegram_chat_id") if payload.get("telegram_chat_id") is not None else (row["telegram_chat_id"] or "")).strip()

    conn.execute(
        """UPDATE client_accounts
           SET email=?, password_hash=?, display_name=?, contact_person=?,
               primary_hotel_id=?, assigned_hotel_ids=?, tier=?, monthly_price=?,
               status=?, alert_email=?, telegram_chat_id=?
           WHERE id=?""",
        (
            email,
            pass_hash,
            display_name,
            contact_person,
            primary_hid,
            json.dumps(assigned_ids),
            tier,
            monthly_price,
            status,
            alert_email,
            tg_chat,
            acc_id,
        ),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM client_accounts WHERE id=?", (acc_id,)).fetchone()
    return {"ok": True, "account": _serialize_account(conn, updated)}


def get_client_portal_data(conn, cfg: dict, account: dict, preview_tier: str = None) -> dict:
    """Strictly isolated data payload for a single Hotel Client Account.
    Contains ONLY the hotels in `account['assigned_hotel_ids']`, their rates, their memory,
    their courtesy call logs, and their strategy tags. Never leaks other accounts or global leads.
    """
    effective_tier_key = preview_tier if (preview_tier and preview_tier in TIER_BY_ID) else (account.get("tier") or "free")
    tier_meta = TIER_BY_ID.get(effective_tier_key, TIER_CATALOG[0])
    primary_hid = int(account["primary_hotel_id"])
    raw_assigned = [int(x) for x in (account.get("assigned_hotel_ids") or [primary_hid])]
    if primary_hid not in raw_assigned:
        raw_assigned.insert(0, primary_hid)

    # Enforce tier comp-set cap (primary hotel + max_competitors)
    max_total = 1 + int(tier_meta.get("max_competitors") or 3)
    scoped_ids = raw_assigned[:max_total]
    hidden_by_tier_count = max(0, len(raw_assigned) - len(scoped_ids))

    rates_by_id = {r["hotel_id"]: r for r in dbmod.latest_rates(conn) if r["hotel_id"] in scoped_ids}
    tags_rows = conn.execute(
        "SELECT * FROM hotel_tags WHERE account_id=? ORDER BY id DESC",
        (account["id"],),
    ).fetchall()
    tags_by_hotel = {}
    all_tags = []
    for tr in tags_rows:
        td = dict(tr)
        if td["hotel_id"] in raw_assigned:
            tags_by_hotel.setdefault(td["hotel_id"], []).append(td)
            all_tags.append(td)

    comp_hotels = []
    for hid in scoped_ids:
        h_row = conn.execute("SELECT * FROM hotels WHERE id=?", (hid,)).fetchone()
        if not h_row:
            continue
        h = dict(h_row)
        r = rates_by_id.get(hid) or {}
        h["price"] = r.get("price")
        h["prev_price"] = r.get("prev_price")
        h["delta_pct"] = r.get("delta_pct", 0.0)
        h["checkin"] = r.get("checkin")
        h["parity_status"] = r.get("parity_status") or "PARITY"
        h["undercut_pct"] = r.get("undercut_pct", 0.0)
        h["ota_channels"] = r.get("ota_channels") or []
        p_now = float(h["price"]) if h["price"] is not None else 0.0
        p_prev = float(h["prev_price"]) if h["prev_price"] is not None else p_now
        occ_info = estimate_occupancy_and_personality(h, p_now, p_prev, h["ota_channels"], float(h["undercut_pct"] or 0.0))
        h["est_occupancy_pct"] = occ_info["est_occupancy_pct"]
        h["pricing_personality"] = occ_info["pricing_personality"]
        h["decision_logic"] = occ_info["decision_logic"]
        h["is_primary"] = (hid == primary_hid)
        h["tags"] = tags_by_hotel.get(hid, [])
        # Include only front-desk phone for courtesy call-arounds inside this comp-set
        ph = conn.execute("SELECT value FROM contacts WHERE hotel_id=? AND kind='phone' LIMIT 1", (hid,)).fetchone()
        h["phone"] = ph["value"] if ph else ""
        comp_hotels.append(h)

    # Sort with primary hotel first, then by price desc
    comp_hotels.sort(key=lambda x: (0 if x["is_primary"] else 1, -(float(x["price"] or 0))))

    my_hotel_row = next((h for h in comp_hotels if h["is_primary"]), comp_hotels[0] if comp_hotels else {})
    neighbor_prices = [float(h["price"]) for h in comp_hotels if not h.get("is_primary") and h.get("price") is not None]
    comp_avg_bar = round(sum(neighbor_prices) / len(neighbor_prices), 0) if neighbor_prices else (float(my_hotel_row.get("price") or 220))
    my_bar = float(my_hotel_row.get("price") or comp_avg_bar or 220)
    spread = round(my_bar - comp_avg_bar, 0)
    undercut_neighbors = [h for h in comp_hotels if h.get("parity_status") == "UNDERCUT"]

    # Actionable Rate Strategy Recommendation for the Client's Primary Hotel
    if my_hotel_row.get("parity_status") == "UNDERCUT" and float(my_hotel_row.get("undercut_pct") or 0) > 2.0:
        rec_action = "FIX OTA PARITY LEAK IMMEDIATELY"
        rec_target_bar = round(my_bar)
        rec_Explain = (
            f"{my_hotel_row['name']} is currently undercut by -{my_hotel_row['undercut_pct']:.1f}% on an OTA channel "
            f"against your ${my_bar:.0f} direct BAR. Close wholesale/FIT discount leaks before raising BAR."
        )
    elif spread < -15:
        rec_action = f"RAISE BAR +${min(28, int(abs(spread) * 0.65))}/NT"
        rec_target_bar = round(my_bar + min(28, int(abs(spread) * 0.65)))
        rec_Explain = (
            f"Your live BAR (${my_bar:.0f}) is ${abs(spread):.0f}/nt below your assigned {my_hotel_row.get('area', 'corridor')} "
            f"comp-set average (${comp_avg_bar:.0f}). You have room to lift BAR without losing conversion."
        )
    elif spread > 25:
        rec_action = "HOLD BAR & MONITOR OCCUPANCY PACE"
        rec_target_bar = round(my_bar)
        rec_Explain = (
            f"Your BAR (${my_bar:.0f}) is positioned +${spread:.0f}/nt above your assigned comp-set average (${comp_avg_bar:.0f}). "
            f"Maintain parity and watch neighbor weekend drops."
        )
    else:
        rec_action = f"OPTIMAL CORRIDOR POSITION (+${max(8, int(my_bar * 0.04))} WKND LIFT)"
        rec_target_bar = round(my_bar + max(8, int(my_bar * 0.04)))
        rec_Explain = (
            f"Your BAR (${my_bar:.0f}) is tightly aligned with your assigned comp-set average (${comp_avg_bar:.0f}). "
            f"Hold weekday BAR and apply a +4% weekend compression lift."
        )

    # Scoped Memory Events (strictly for scoped_ids)
    placeholders = ",".join("?" for _ in scoped_ids)
    mem_rows = [
        dict(r)
        for r in conn.execute(
            f"""SELECT m.*, h.name as hotel_name, h.area
                FROM memory_events m
                JOIN hotels h ON h.id = m.hotel_id
                WHERE m.hotel_id IN ({placeholders})
                ORDER BY m.recorded_at DESC LIMIT 30""",
            scoped_ids,
        ).fetchall()
    ]

    # Scoped Courtesy Call Logs (strictly for scoped_ids)
    call_rows = [
        dict(r)
        for r in conn.execute(
            f"""SELECT c.*, h.name as hotel_name, h.area
                FROM call_logs c
                JOIN hotels h ON h.id = c.hotel_id
                WHERE c.hotel_id IN ({placeholders})
                ORDER BY c.called_at DESC LIMIT 20""",
            scoped_ids,
        ).fetchall()
    ]

    # Generate inline SVG visual charts scoped strictly to my_hotel_row & comp_hotels
    nb_for_svg = [
        {"name": h["name"], "price": h.get("price")}
        for h in comp_hotels if not h.get("is_primary") and h.get("price")
    ]
    fallback_nm = account.get("display_name") or "Miami Hotel"
    ota_svg = build_ota_ladder_svg(
        my_hotel_row.get("name") or fallback_nm,
        float(my_hotel_row.get("price") or 0),
        my_hotel_row.get("ota_channels") or [],
    ) if my_hotel_row else ""
    comp_svg = build_comp_set_svg(
        my_hotel_row.get("name") or fallback_nm,
        float(my_hotel_row.get("price") or comp_avg_bar or 0),
        nb_for_svg,
    ) if my_hotel_row else ""

    return {
        "ok": True,
        "isolated_tenant": True,
        "account": account,
        "active_tier": tier_meta,
        "all_tiers": TIER_CATALOG,
        "hidden_by_tier_count": hidden_by_tier_count,
        "total_assigned_in_account": len(raw_assigned),
        "primary_hotel": my_hotel_row,
        "comp_set": comp_hotels,
        "graphics": {
            "ota_ladder_svg": ota_svg,
            "comp_set_svg": comp_svg,
        },
        "strategy": {
            "my_bar": my_bar,
            "comp_avg_bar": comp_avg_bar,
            "spread_vs_comp": spread,
            "undercut_count_in_comp": len(undercut_neighbors),
            "recommended_action": rec_action,
            "recommended_target_bar": rec_target_bar,
            "explanation": rec_Explain,
            "staff_hours_saved_mo": tier_meta["staff_hours_saved_mo"],
            "labor_dollars_saved_mo": tier_meta["labor_dollars_saved_mo"],
            "est_revenue_recovered_mo": tier_meta["est_revenue_recovered_mo"],
        },
        "memory_events": mem_rows,
        "call_logs": call_rows,
        "call_templates": COURTESY_CALL_TEMPLATES,
        "tags": all_tags,
        "compression_events": MIAMI_COMPRESSION_EVENTS,
    }


def add_client_hotel_tag(conn, account: dict, payload: dict) -> dict:
    """Add a strategy tag/note to a hotel ONLY if that hotel is in the client's assigned comp-set."""
    hid = int(payload.get("hotel_id") or account["primary_hotel_id"])
    assigned = [int(x) for x in (account.get("assigned_hotel_ids") or [])]
    if hid not in assigned:
        return {"ok": False, "error": "Access Denied: You can only tag hotels assigned to your isolated account.", "forbidden": True}
    tag = (payload.get("tag") or "").strip()
    if not tag:
        return {"ok": False, "error": "Tag label is required."}
    note = (payload.get("note") or "").strip()
    color = (payload.get("color") or "#facc15").strip()
    conn.execute(
        "INSERT INTO hotel_tags(account_id, hotel_id, tag, note, color, created_at) VALUES (?,?,?,?,?,?)",
        (account["id"], hid, tag, note, color, time.time()),
    )
    conn.commit()
    return {"ok": True, "hotel_id": hid, "tag": tag}


def delete_client_hotel_tag(conn, account: dict, tag_id: int) -> dict:
    conn.execute("DELETE FROM hotel_tags WHERE id=? AND account_id=?", (int(tag_id), account["id"]))
    conn.commit()
    return {"ok": True, "deleted_id": int(tag_id)}


def client_scrape_comp_set(conn, cfg: dict, account: dict) -> dict:
    """Run live Xotelo + JSON-LD rate scraping strictly for the hotels assigned to this client account."""
    from .rate_engine import scrape_rate_intelligence

    tier_meta = TIER_BY_ID.get(account.get("tier") or "free", TIER_CATALOG[0])
    max_total = 1 + int(tier_meta.get("max_competitors") or 3)
    assigned = [int(x) for x in (account.get("assigned_hotel_ids") or [account["primary_hotel_id"]])][:max_total]

    stay = cfg["stay"]
    checkin = (date.today() + timedelta(days=stay["checkin_days_out"])).isoformat()
    checkout = (date.today() + timedelta(days=stay["checkin_days_out"] + stay["nights"])).isoformat()
    run_id = dbmod.new_run(conn, mode=f"client-scrape:{account['username']}")
    rates_new = 0
    for hid in assigned:
        h_row = conn.execute("SELECT * FROM hotels WHERE id=?", (hid,)).fetchone()
        if not h_row:
            continue
        intel = scrape_rate_intelligence(dict(h_row), cfg, checkin=checkin, checkout=checkout, check_jsonld=False, log=lambda s: None)
        p_val = intel.get("direct_price")
        if p_val is not None:
            dbmod.add_rate(
                conn,
                hid,
                run_id,
                intel.get("source") or "xotelo",
                checkin,
                checkout,
                float(p_val),
                cfg["currency"],
                intel.get("room_type") or "Standard Room",
                ota_json=intel.get("channels") or [],
                parity_status=intel.get("parity_status") or "PARITY",
                undercut_pct=intel.get("undercut_pct") or 0.0,
            )
            record_and_analyze_memory(conn, hid)
            rates_new += 1
    dbmod.finish_run(conn, run_id, status="ok", hotels_attempted=len(assigned), hotels_ok=rates_new, contacts_new=0, rates_new=rates_new)
    return {"ok": True, "account": account["username"], "hotels_scanned": len(assigned), "live_rates_updated": rates_new}


def list_marketing_campaigns(conn, status_filter: str = "") -> list:
    sql = """SELECT mc.*, h.name as hotel_name, h.area
             FROM marketing_campaigns mc
             LEFT JOIN hotels h ON h.id = mc.hotel_id"""
    params = ()
    if status_filter:
        sql += " WHERE mc.approval_status=?"
        params = (status_filter,)
    sql += " ORDER BY CASE mc.approval_status WHEN 'pending_approval' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END, mc.id DESC LIMIT 100"
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def approve_or_dispatch_campaign(conn, cfg: dict, payload: dict) -> dict:
    """Mission Control action: approve, reject, edit, or dispatch a campaign (or batch of campaigns)."""
    action = (payload.get("action") or "approve_and_send").strip().lower()
    camp_id = payload.get("campaign_id")
    now = time.time()

    if action == "approve_all_pending":
        pending = conn.execute("SELECT id FROM marketing_campaigns WHERE approval_status='pending_approval'").fetchall()
        dispatched = []
        for r in pending:
            res = approve_or_dispatch_campaign(conn, cfg, {"campaign_id": r["id"], "action": "approve_and_send"})
            dispatched.append(res)
        return {"ok": True, "batch_approved": len(dispatched), "results": dispatched}

    if action == "generate_corridor_batch":
        corridor = (payload.get("area") or "").strip()
        channel = (payload.get("channel") or "email").strip().lower()
        target_tier = (payload.get("target_tier") or "free_to_99").strip()
        leads = list_verified_leads(conn, price_monthly=99).get("leads") or []
        created = 0
        for ld in leads:
            if corridor and ld.get("area") != corridor:
                continue
            hid = ld["hotel_id"]
            recip = ld.get("email") if channel == "email" else ld.get("phone")
            if not recip:
                continue
            reg_url = f"{_base_url(cfg)}/website?hotel_id={hid}#register"
            demo_url = f"{_base_url(cfg)}/portal?demo_hotel={hid}"
            person = ld.get("person_name") or f"{ld['name']} GM"
            short_h = ld.get("short_name") or ld["name"].split(",")[0].strip()
            ota_nm = (ld.get("lowest_ota_name") or "ota").lower()
            if ld.get("parity_status") == "UNDERCUT" and ld.get("price"):
                subj = f"{short_h.lower()} rate on {ota_nm} today"
            else:
                subj = f"quick {ld['area'].lower()} rate check for {short_h.lower()}"
            first_person = person.split("/")[0].split("(")[0].strip()
            body = (
                f"Hi {first_person},\n\n"
                f"I live right here in North Miami and built a daily 6 AM rate & OTA undercut tracker for independent {ld['area']} hotels "
                f"(Free $0 starter tier, or $99/mo flat with no contract).\n\n"
                f"Today's live scan on {short_h}: {ld.get('proof_line') or ''} (saves ~45 hrs/mo of staff rate checks across your corridor).\n\n"
                f"Want me to send tomorrow's 6 AM rate sheet for {short_h}, or peek at your hotel's live demo panel at {demo_url} (free claim: {reg_url})?\n\n"
                f"Best,\nJasmel Acosta · North Miami, FL 33161 (Reply STOP to opt out)"
            )
            conn.execute(
                """INSERT INTO marketing_campaigns(
                     hotel_id, campaign_name, channel, target_tier, recipient,
                     person_name, subject, body, registration_url, approval_status, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (hid, f"YC 3-Sentence · {ld['area']} {channel.upper()}", channel, target_tier, recip, person, subj, body, reg_url, "pending_approval", now),
            )
            created += 1
            if created >= 10:
                break
        conn.commit()
        return {"ok": True, "created_count": created}

    row = conn.execute("SELECT * FROM marketing_campaigns WHERE id=?", (int(camp_id or 0),)).fetchone()
    if not row:
        return {"ok": False, "error": "Campaign item not found"}

    if payload.get("body"):
        conn.execute("UPDATE marketing_campaigns SET body=?, subject=? WHERE id=?", (payload["body"], payload.get("subject") or row["subject"], row["id"]))
        conn.commit()
        row = conn.execute("SELECT * FROM marketing_campaigns WHERE id=?", (row["id"],)).fetchone()

    if action == "reject":
        conn.execute("UPDATE marketing_campaigns SET approval_status='rejected', approved_by='jasmel', approved_at=? WHERE id=?", (now, row["id"]))
        conn.commit()
        return {"ok": True, "campaign_id": row["id"], "approval_status": "rejected"}

    # Approve and send/queue via outreach_engine
    out_res = send_or_queue_outreach(
        conn,
        cfg,
        {
            "hotel_id": row["hotel_id"] or 1,
            "channel": row["channel"] if row["channel"] in ("email", "sms", "whatsapp", "voice") else "email",
            "recipient": row["recipient"],
            "subject": row["subject"],
            "body": row["body"],
            "price_monthly": 99,
        },
    )
    conn.execute(
        "UPDATE marketing_campaigns SET approval_status='dispatched', approved_by='jasmel', approved_at=?, dispatched_at=? WHERE id=?",
        (now, now, row["id"]),
    )
    conn.commit()
    return {
        "ok": True,
        "campaign_id": row["id"],
        "approval_status": "dispatched",
        "outreach_result": out_res,
    }


def get_public_website_payload(conn, cfg: dict) -> dict:
    """Data payload for the Public Marketing & Registration Website (`/`, `/website`).
    Exposes live Miami market stats, Mock Demo Client #1 preview, tier comparison (Free -> $99 -> $199),
    competitor comparison matrix, owner callback status, and all hotels with personalized Panel Demo URLs.
    """
    ensure_seed_accounts_and_campaigns(conn, cfg)
    mr = build_market_research_and_posts(conn)
    demo_acc = conn.execute("SELECT * FROM client_accounts WHERE username='avalon' OR is_demo=1 ORDER BY id ASC LIMIT 1").fetchone()
    demo_portal = get_client_portal_data(conn, cfg, _serialize_account(conn, demo_acc)) if demo_acc else {}
    rates_by_id = {r["hotel_id"]: r for r in dbmod.latest_rates(conn)}
    demo_samples = []
    for sample_id, sample_label in ((1, "Sample Demo #1 · North Beach All-Suites"), (2, "Sample Demo #2 · Boutique Beachfront"), (4, "Sample Demo #3 · South Beach Art Deco")):
        row = conn.execute("SELECT id, name, area, stars, est_rooms FROM hotels WHERE id=?", (sample_id,)).fetchone()
        if row:
            d = dict(row)
            rt = rates_by_id.get(d["id"]) or {}
            demo_samples.append({
                "id": d["id"],
                "name": sample_label,
                "area": d["area"],
                "stars": d["stars"],
                "est_rooms": d["est_rooms"],
                "price": round(float(rt["price"])) if rt.get("price") is not None else None,
                "parity_status": rt.get("parity_status") or "SAMPLE_LIVE",
                "undercut_pct": float(rt.get("undercut_pct") or 0.0),
                "demo_url": f"/portal?demo_hotel={d['id']}",
                "audit_url": f"/audit?hotel_id={d['id']}",
            })
    out_cfg = cfg.get("outreach") or {}
    return {
        "ok": True,
        "market_summary": mr.get("summary") or {},
        "corridors": mr.get("corridors") or [],
        "tiers": TIER_CATALOG,
        "comparison_matrix": COMPETITOR_COMPARISON_MATRIX,
        "owner_callback_phone": (out_cfg.get("sender_phone") or "").strip(),
        "demo_client_preview": {
            "username": "avalon",
            "password_hint": "demo1234",
            "portal_demo_url": "/portal?demo=1",
            "hotel_name": "Sample Boutique Demo #1",
            "area": "South Beach",
            "strategy": demo_portal.get("strategy") or {},
            "comp_set_sample": (demo_portal.get("comp_set") or [])[:4],
        },
        "hotels_directory": demo_samples,
    }


def get_mission_control_overview(conn, cfg: dict, price_monthly: int = 99) -> dict:
    """Complete God-Mode payload for Jasmel's Administrator Mission Control (`/mission-control`)."""
    ensure_seed_accounts_and_campaigns(conn, cfg)
    accounts = list_client_accounts(conn)
    campaigns = list_marketing_campaigns(conn)
    leads_bundle = list_verified_leads(conn, price_monthly=price_monthly)
    mr = build_market_research_and_posts(conn)
    outreach_logs = list_outreach_log(conn, limit=50)
    callbacks = [
        dict(r)
        for r in conn.execute(
            """SELECT c.*, h.name AS hotel_name FROM call_logs c
               LEFT JOIN hotels h ON h.id = c.hotel_id
               WHERE c.shift LIKE 'Inbound Website%' OR c.caller_mode LIKE '%Auditor%'
               ORDER BY c.called_at DESC LIMIT 25"""
        ).fetchall()
    ]
    readiness = get_channel_readiness(cfg)
    hotels_all = [
        dict(r)
        for r in conn.execute("SELECT id, name, area, stars, est_rooms, deal_stage FROM hotels ORDER BY area, name").fetchall()
    ]
    pending_cnt = sum(1 for c in campaigns if c.get("approval_status") == "pending_approval")
    approved_cnt = sum(1 for c in campaigns if c.get("approval_status") in ("approved", "dispatched"))
    return {
        "ok": True,
        "owner": (cfg.get("admin_auth") or {}).get("owner_name") or "Jasmel Acosta",
        "tiers": TIER_CATALOG,
        "comparison_matrix": COMPETITOR_COMPARISON_MATRIX,
        "accounts": accounts,
        "campaigns": campaigns,
        "campaign_counts": {
            "total": len(campaigns),
            "pending_approval": pending_cnt,
            "approved_or_dispatched": approved_cnt,
        },
        "leads_bundle": leads_bundle,
        "market_research": mr,
        "outreach_logs": outreach_logs,
        "callback_and_auditor_calls": callbacks,
        "outreach_readiness": readiness,
        "hotels_directory": hotels_all,
    }
