"""SQLite storage. Schema is deliberately small and queryable by hand.

Tables
  hotels    – one row per property in the competitive set
  contacts  – people/addresses found on the hotel's own site (the "get the contact" layer)
  rates     – one price observation per hotel per run (source: ota | direct | xotelo | manual)
  runs      – collector executions (status + stats)
  prospects – hotels scored by "who needs rate intelligence" heuristics
"""
import json, re, sqlite3, time

SCHEMA = """
CREATE TABLE IF NOT EXISTS hotels (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  area TEXT,
  website TEXT,
  booking_url TEXT,
  stars REAL,
  est_rooms INTEGER,
  brand TEXT DEFAULT 'independent',
  latitude REAL, longitude REAL,
  xotelo_key TEXT,
  booking_engine TEXT DEFAULT 'Direct / SynXis',
  review_rating REAL,
  review_count INTEGER,
  price_min REAL,
  price_max REAL,
  deal_stage TEXT DEFAULT 'new',
  created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY,
  hotel_id INTEGER NOT NULL REFERENCES hotels(id),
  kind TEXT NOT NULL,            -- phone | email | person | address | linkedin | instagram
  value TEXT NOT NULL,
  context TEXT,                  -- where it was found: homepage /contact /GM ...
  verified_status TEXT DEFAULT 'scraped', -- mx_verified | http_verified | public_record_verified | manual_verified
  person_title TEXT,
  source_url TEXT,
  confidence REAL DEFAULT 0.85,
  found_at REAL NOT NULL,
  UNIQUE(hotel_id, kind, value)
);
CREATE TABLE IF NOT EXISTS rates (
  id INTEGER PRIMARY KEY,
  hotel_id INTEGER NOT NULL REFERENCES hotels(id),
  run_id INTEGER,
  source TEXT NOT NULL DEFAULT 'direct',
  checkin TEXT, checkout TEXT,
  nightly_price REAL, currency TEXT DEFAULT 'USD',
  room_type TEXT,
  ota_json TEXT,                 -- JSON list of {name, rate, code} for multi-OTA parity
  parity_status TEXT,            -- UNDERCUT | PARITY | DIRECT_WIN
  undercut_pct REAL DEFAULT 0,
  scraped_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rates_hotel ON rates(hotel_id, scraped_at);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  started REAL NOT NULL, finished REAL,
  mode TEXT, status TEXT DEFAULT 'running',
  hotels_attempted INTEGER DEFAULT 0, hotels_ok INTEGER DEFAULT 0,
  contacts_new INTEGER DEFAULT 0, rates_new INTEGER DEFAULT 0,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS prospects (
  hotel_id INTEGER PRIMARY KEY REFERENCES hotels(id),
  score INTEGER NOT NULL,        -- 0..100
  tier TEXT NOT NULL,            -- hot | warm | watch
  signals TEXT,                  -- JSON list of reasons
  est_annual_upside INTEGER DEFAULT 0,
  scored_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS memory_events (
  id INTEGER PRIMARY KEY,
  hotel_id INTEGER NOT NULL REFERENCES hotels(id),
  event_type TEXT NOT NULL,      -- rate_change | parity_violation | competitor_move | occupancy_signal | strategy_decision | overnight_call
  old_price REAL,
  new_price REAL,
  delta_pct REAL DEFAULT 0,
  est_occupancy_pct INTEGER DEFAULT 74,
  competitor_pattern TEXT,       -- AGGRESSIVE_YIELD | DISCOUNT_DUMP | WHOLESALE_LEAK | HOLD_STEADY
  ai_recommendation TEXT,
  recorded_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_hotel ON memory_events(hotel_id, recorded_at);
CREATE TABLE IF NOT EXISTS call_logs (
  id INTEGER PRIMARY KEY,
  hotel_id INTEGER NOT NULL REFERENCES hotels(id),
  shift TEXT DEFAULT 'Overnight Audit (11PM–4AM)',
  caller_mode TEXT DEFAULT 'Courtesy Call-Around',
  phone_dialed TEXT,
  reported_occupancy_pct INTEGER,
  rooms_left INTEGER,
  quoted_walkin_rate REAL,
  questions_asked TEXT,
  transcript TEXT,
  recording_url TEXT,
  status TEXT DEFAULT 'queued_awaiting_voice_key',
  called_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_calls_hotel ON call_logs(hotel_id, called_at);
CREATE TABLE IF NOT EXISTS outreach_log (
  id INTEGER PRIMARY KEY,
  hotel_id INTEGER NOT NULL REFERENCES hotels(id),
  channel TEXT NOT NULL,          -- email | sms | whatsapp | voice | walk_in
  recipient TEXT NOT NULL,        -- email address or E.164 phone
  person_name TEXT,
  offer_price_monthly INTEGER DEFAULT 99,
  offer_label TEXT,
  subject TEXT,
  body TEXT NOT NULL,
  provider TEXT,                  -- smtp | brevo | resend | twilio_sms | twilio_whatsapp | vapi | bland | twilio_voice | dry_run
  status TEXT NOT NULL,           -- queued_dry_run | ready_awaiting_credentials | sent_live | failed | opted_out
  provider_message_id TEXT,
  error_detail TEXT,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outreach_hotel ON outreach_log(hotel_id, created_at);
CREATE TABLE IF NOT EXISTS do_not_contact (
  value TEXT PRIMARY KEY,
  channel TEXT,
  reason TEXT,
  added_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS client_accounts (
  id INTEGER PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  contact_person TEXT,
  primary_hotel_id INTEGER NOT NULL REFERENCES hotels(id),
  assigned_hotel_ids TEXT NOT NULL,
  tier TEXT NOT NULL DEFAULT 'free',
  monthly_price INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'active',
  is_demo INTEGER NOT NULL DEFAULT 0,
  alert_email TEXT,
  telegram_chat_id TEXT,
  session_token TEXT,
  last_login_at REAL,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS hotel_tags (
  id INTEGER PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES client_accounts(id),
  hotel_id INTEGER NOT NULL REFERENCES hotels(id),
  tag TEXT NOT NULL,
  note TEXT,
  color TEXT DEFAULT '#facc15',
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tags_account ON hotel_tags(account_id, hotel_id);
CREATE TABLE IF NOT EXISTS marketing_campaigns (
  id INTEGER PRIMARY KEY,
  hotel_id INTEGER REFERENCES hotels(id),
  campaign_name TEXT NOT NULL,
  channel TEXT NOT NULL,
  target_tier TEXT DEFAULT 'free_to_99',
  recipient TEXT,
  person_name TEXT,
  subject TEXT,
  body TEXT NOT NULL,
  registration_url TEXT,
  approval_status TEXT DEFAULT 'pending_approval',
  approved_by TEXT,
  approved_at REAL,
  dispatched_at REAL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON marketing_campaigns(approval_status, created_at);
CREATE TABLE IF NOT EXISTS room_inventory_ops (
  hotel_id INTEGER PRIMARY KEY REFERENCES hotels(id),
  total_rooms INTEGER NOT NULL DEFAULT 45,
  rooms_sold INTEGER NOT NULL DEFAULT 32,
  ooo_rooms INTEGER NOT NULL DEFAULT 0,
  oos_rooms INTEGER NOT NULL DEFAULT 0,
  housekeeping_hold INTEGER NOT NULL DEFAULT 0,
  status_flags TEXT DEFAULT '[]',
  operational_tags TEXT DEFAULT '[]',
  room_types_json TEXT DEFAULT '[]',
  notes TEXT DEFAULT '',
  updated_by TEXT DEFAULT 'Reservations Desk',
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS auto_pricing_rules (
  hotel_id INTEGER PRIMARY KEY REFERENCES hotels(id),
  mode TEXT NOT NULL DEFAULT 'semi_auto',
  min_bar_floor REAL NOT NULL DEFAULT 119,
  max_bar_ceiling REAL NOT NULL DEFAULT 699,
  compression_occ_threshold INTEGER NOT NULL DEFAULT 85,
  compression_lift_pct REAL NOT NULL DEFAULT 12.0,
  parity_auto_protect INTEGER NOT NULL DEFAULT 1,
  comp_position_target TEXT NOT NULL DEFAULT 'match_avg',
  telegram_alerts_enabled INTEGER NOT NULL DEFAULT 1,
  telegram_chat_id TEXT DEFAULT '',
  alert_tags TEXT DEFAULT '["#OOO","#ParityLeak","#Compression","#Housekeeping"]',
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS pricing_actions_log (
  id INTEGER PRIMARY KEY,
  hotel_id INTEGER NOT NULL REFERENCES hotels(id),
  room_category TEXT DEFAULT 'All Room Types (BAR)',
  old_bar REAL,
  new_bar REAL,
  sellable_rooms INTEGER,
  net_occupancy_pct REAL,
  trigger_tags TEXT DEFAULT '[]',
  reason TEXT NOT NULL,
  action_status TEXT NOT NULL DEFAULT 'applied',
  pms_payload TEXT,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pricing_actions_hotel ON pricing_actions_log(hotel_id, created_at);
CREATE TABLE IF NOT EXISTS competitor_inquiries (
  id INTEGER PRIMARY KEY,
  requester_hotel_id INTEGER NOT NULL REFERENCES hotels(id),
  target_hotel_id INTEGER REFERENCES hotels(id),
  target_hotel_name TEXT NOT NULL,
  target_email TEXT,
  inquiry_type TEXT NOT NULL DEFAULT 'courtesy_rate_swap',
  checkin TEXT,
  rooms_requested INTEGER DEFAULT 1,
  subject TEXT,
  body TEXT NOT NULL,
  quoted_rate REAL,
  status TEXT NOT NULL DEFAULT 'drafted',
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comp_inquiries_req ON competitor_inquiries(requester_hotel_id, created_at);
"""

MIGRATIONS = [
    ("hotels", "xotelo_key", "TEXT"),
    ("hotels", "booking_engine", "TEXT DEFAULT 'Direct Website'"),
    ("hotels", "review_rating", "REAL"),
    ("hotels", "review_count", "INTEGER"),
    ("hotels", "price_min", "REAL"),
    ("hotels", "price_max", "REAL"),
    ("hotels", "deal_stage", "TEXT DEFAULT 'new'"),
    ("hotels", "est_occupancy_pct", "INTEGER DEFAULT 74"),
    ("hotels", "pricing_personality", "TEXT DEFAULT 'Dynamic Responder'"),
    ("hotels", "management_group", "TEXT"),
    ("hotels", "website_status", "TEXT DEFAULT 'unknown'"),
    ("contacts", "verified_status", "TEXT DEFAULT 'scraped'"),
    ("contacts", "person_title", "TEXT"),
    ("contacts", "source_url", "TEXT"),
    ("rates", "ota_json", "TEXT"),
    ("rates", "parity_status", "TEXT"),
    ("rates", "undercut_pct", "REAL DEFAULT 0"),
    ("rates", "est_occupancy_pct", "INTEGER DEFAULT 74"),
    ("prospects", "est_annual_upside", "INTEGER DEFAULT 0"),
    ("contacts", "department", "TEXT DEFAULT 'general_info'"),
    ("outreach_log", "delivery_status", "TEXT DEFAULT 'pending'"),
    ("outreach_log", "opened_at", "REAL"),
    ("outreach_log", "clicked_at", "REAL"),
    ("outreach_log", "bounced_at", "REAL"),
]


def open_db(path):
    conn = sqlite3.connect(path, timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA journal_mode=WAL")
    has_schema = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='competitor_inquiries'"
    ).fetchone()
    if not has_schema:
        conn.executescript(SCHEMA)
    # Ensure latest columns exist idempotently
    existing_contact_cols = {r["name"] for r in conn.execute("PRAGMA table_info(contacts)").fetchall()}
    existing_outreach_cols = {r["name"] for r in conn.execute("PRAGMA table_info(outreach_log)").fetchall()}
    if "department" not in existing_contact_cols or "delivery_status" not in existing_outreach_cols or not has_schema:
        for table, col, coldef in MIGRATIONS:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")
            except sqlite3.OperationalError:
                pass
        conn.commit()
    # Ensure standards-compliant email bounce/block/suppression & event tracking tables exist
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS email_suppressions (
          email TEXT PRIMARY KEY,
          domain TEXT,
          reason TEXT NOT NULL,
          soft_bounce_count INTEGER DEFAULT 0,
          suppress_domain INTEGER DEFAULT 0,
          detail TEXT,
          updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS email_events (
          id INTEGER PRIMARY KEY,
          resend_id TEXT,
          email TEXT,
          event_type TEXT NOT NULL,
          bounce_type TEXT,
          subject TEXT,
          raw_json TEXT,
          received_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_email_events_email ON email_events(email, received_at);
        CREATE TABLE IF NOT EXISTS campaign_sends (
          id INTEGER PRIMARY KEY,
          hotel_id INTEGER NOT NULL,
          email TEXT NOT NULL,
          department TEXT,
          step_number INTEGER NOT NULL,
          subject TEXT,
          resend_id TEXT,
          status TEXT NOT NULL,
          delivery_status TEXT DEFAULT 'sent',
          sent_at REAL NOT NULL,
          UNIQUE(email, step_number)
        );
        """
    )
    conn.commit()
    return conn


def normalize_contact_value(kind, value):
    """Clean and normalize emails, phones, and addresses to prevent noisy duplicates."""
    value = (value or "").strip()
    if not value:
        return ""
    if kind == "email":
        value = re.sub(r"^mailto:", "", value, flags=re.I).split("?")[0].strip().lower()
        if not re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", value):
            return ""
        return value
    if kind == "phone":
        value = re.sub(r"^tel:", "", value, flags=re.I).strip()
        digits = re.sub(r"\D", "", value)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        if 10 < len(digits) <= 13:
            return f"+{digits}"
        return ""
    if kind == "address":
        value = " ".join(value.split()).rstrip(".")
        # Remove leading junk like "3373 LOCATION 826 Ocean Drive"
        m = re.search(r"(\d{2,5}\s+(?:Ocean|Collins|Washington|Indian Creek|Pine Tree|Island|James|Drexel|Espa[nñ]ola|Lincoln|Meridian|Alton|20th|21st|41st)[A-Za-z0-9\s.,'-]*)", value, re.I)
        if m:
            value = m.group(1).strip().rstrip(".")
        if len(value) < 8 or len(value) > 75 or "get directions" in value.lower() or "along the famed" in value.lower():
            return ""
        return value
    return value


def upsert_hotel(conn, **kw):
    row = conn.execute("SELECT id FROM hotels WHERE name=?", (kw["name"],)).fetchone()
    if row:
        hid = row["id"]
        conn.execute(
            """UPDATE hotels SET
               area=COALESCE(?, area),
               website=COALESCE(?, website),
               booking_url=COALESCE(?, booking_url),
               stars=COALESCE(?, stars),
               est_rooms=COALESCE(?, est_rooms),
               brand=COALESCE(?, brand),
               latitude=COALESCE(?, latitude),
               longitude=COALESCE(?, longitude),
               xotelo_key=COALESCE(?, xotelo_key),
               booking_engine=COALESCE(?, booking_engine),
               review_rating=COALESCE(?, review_rating),
               review_count=COALESCE(?, review_count),
               price_min=COALESCE(?, price_min),
               price_max=COALESCE(?, price_max),
               management_group=COALESCE(?, management_group),
               website_status=COALESCE(?, website_status)
               WHERE id=?""",
            (kw.get("area"), kw.get("website"), kw.get("booking_url"),
             kw.get("stars"), kw.get("est_rooms"), kw.get("brand"),
             kw.get("latitude"), kw.get("longitude"), kw.get("xotelo_key"),
             kw.get("booking_engine"), kw.get("review_rating"), kw.get("review_count"),
             kw.get("price_min"), kw.get("price_max"),
             kw.get("management_group"), kw.get("website_status"), hid))
        conn.commit()
        return hid
    cur = conn.execute(
        """INSERT INTO hotels(
           name,area,website,booking_url,stars,est_rooms,brand,latitude,longitude,
           xotelo_key,booking_engine,review_rating,review_count,price_min,price_max,
           deal_stage,management_group,website_status,created)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (kw.get("name"), kw.get("area"), kw.get("website"), kw.get("booking_url"),
         kw.get("stars"), kw.get("est_rooms"), kw.get("brand", "independent"),
         kw.get("latitude"), kw.get("longitude"), kw.get("xotelo_key"),
         kw.get("booking_engine", "Direct Website"), kw.get("review_rating"),
         kw.get("review_count"), kw.get("price_min"), kw.get("price_max"),
         kw.get("deal_stage", "new"), kw.get("management_group"),
         kw.get("website_status", "unknown"), time.time()))
    conn.commit()
    return cur.lastrowid


def add_contact(conn, hotel_id, kind, value, context="", confidence=0.85,
                verified_status="scraped", person_title=None, source_url=None):
    clean = normalize_contact_value(kind, value)
    if not clean:
        return False
    try:
        before = conn.total_changes
        conn.execute(
            """INSERT INTO contacts(hotel_id,kind,value,context,verified_status,person_title,source_url,confidence,found_at)
               VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(hotel_id, kind, value) DO UPDATE SET
                 verified_status=CASE WHEN excluded.verified_status != 'scraped' THEN excluded.verified_status ELSE contacts.verified_status END,
                 person_title=COALESCE(excluded.person_title, contacts.person_title),
                 source_url=COALESCE(excluded.source_url, contacts.source_url),
                 confidence=MAX(contacts.confidence, excluded.confidence)""",
            (hotel_id, kind, clean, context, verified_status, person_title, source_url, confidence, time.time()))
        conn.commit()
        return conn.total_changes > before
    except sqlite3.Error:
        return False


def add_rate(conn, hotel_id, run_id, source, checkin, checkout, nightly_price, currency,
             room_type=None, ota_json=None, parity_status=None, undercut_pct=0.0, scraped_at=None):
    if isinstance(ota_json, (list, dict)):
        ota_json = json.dumps(ota_json)
    conn.execute(
        """INSERT INTO rates(hotel_id,run_id,source,checkin,checkout,nightly_price,currency,
           room_type,ota_json,parity_status,undercut_pct,scraped_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (hotel_id, run_id, source, checkin, checkout, nightly_price, currency,
         room_type, ota_json, parity_status, undercut_pct or 0.0, scraped_at or time.time()))
    conn.commit()


def new_run(conn, mode):
    cur = conn.execute("INSERT INTO runs(started,mode) VALUES(?,?)", (time.time(), mode))
    conn.commit()
    return cur.lastrowid


def finish_run(conn, run_id, **stats):
    conn.execute(
        "UPDATE runs SET finished=?, status=?, hotels_attempted=?, hotels_ok=?, contacts_new=?, rates_new=?, notes=?"
        " WHERE id=?",
        (time.time(), stats.get("status", "ok"), stats.get("hotels_attempted", 0),
         stats.get("hotels_ok", 0), stats.get("contacts_new", 0), stats.get("rates_new", 0),
         stats.get("notes", ""), run_id))
    conn.commit()


def latest_rates(conn):
    """Most recent nightly price per hotel, with previous price, timestamps, OTA ladder, and parity status.
    Uses LEFT JOIN so hotels with NO_LIVE_QUOTE are still returned cleanly without fake rates.
    """
    rows = [dict(r) for r in conn.execute("""
      SELECT h.id AS hotel_id, h.name, h.area, h.stars, h.est_rooms, h.brand,
             h.booking_engine, h.price_min, h.price_max, h.review_rating, h.review_count,
             h.website, h.xotelo_key, h.management_group, h.website_status, h.deal_stage,
             r1.nightly_price AS price, COALESCE(r1.currency, 'USD') AS currency,
             COALESCE(r1.source, 'no_live_quote') AS source, r1.checkin, r1.checkout,
             r1.room_type, r1.ota_json,
             COALESCE(r1.parity_status, 'NO_LIVE_QUOTE') AS parity_status,
             COALESCE(r1.undercut_pct, 0.0) AS undercut_pct, r1.scraped_at,
             (SELECT r2.nightly_price FROM rates r2
               WHERE r2.hotel_id=h.id AND r2.nightly_price IS NOT NULL AND (r1.id IS NULL OR r2.id < r1.id)
               ORDER BY r2.id DESC LIMIT 1) AS prev_price,
             (SELECT r2.scraped_at FROM rates r2
               WHERE r2.hotel_id=h.id AND r2.nightly_price IS NOT NULL AND (r1.id IS NULL OR r2.id < r1.id)
               ORDER BY r2.id DESC LIMIT 1) AS prev_scraped_at
      FROM hotels h
      LEFT JOIN rates r1 ON r1.id = (
        SELECT id FROM rates WHERE hotel_id=h.id AND nightly_price IS NOT NULL ORDER BY id DESC LIMIT 1)
      ORDER BY h.name""")]
    for r in rows:
        try:
            r["ota_channels"] = json.loads(r.get("ota_json") or "[]")
        except Exception:
            r["ota_channels"] = []
        if r.get("price") and r.get("prev_price"):
            r["delta_dollar"] = round(r["price"] - r["prev_price"], 2)
            r["delta_pct"] = round((r["price"] - r["prev_price"]) / r["prev_price"] * 100, 1)
        else:
            r["delta_dollar"] = 0.0
            r["delta_pct"] = 0.0
    return rows


def count_contacts(conn, hotel_id):
    return conn.execute("SELECT COUNT(*) c FROM contacts WHERE hotel_id=?", (hotel_id,)).fetchone()["c"]
