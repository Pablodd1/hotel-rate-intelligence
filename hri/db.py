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
  status TEXT DEFAULT 'completed',
  called_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_calls_hotel ON call_logs(hotel_id, called_at);
"""

MIGRATIONS = [
    ("hotels", "xotelo_key", "TEXT"),
    ("hotels", "booking_engine", "TEXT DEFAULT 'Direct / SynXis'"),
    ("hotels", "review_rating", "REAL"),
    ("hotels", "review_count", "INTEGER"),
    ("hotels", "price_min", "REAL"),
    ("hotels", "price_max", "REAL"),
    ("hotels", "deal_stage", "TEXT DEFAULT 'new'"),
    ("hotels", "est_occupancy_pct", "INTEGER DEFAULT 74"),
    ("hotels", "pricing_personality", "TEXT DEFAULT 'Dynamic Responder'"),
    ("rates", "ota_json", "TEXT"),
    ("rates", "parity_status", "TEXT"),
    ("rates", "undercut_pct", "REAL DEFAULT 0"),
    ("rates", "est_occupancy_pct", "INTEGER DEFAULT 74"),
    ("prospects", "est_annual_upside", "INTEGER DEFAULT 0"),
]


def open_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    for table, col, coldef in MIGRATIONS:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")
        except sqlite3.OperationalError:
            pass
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
               price_max=COALESCE(?, price_max)
               WHERE id=?""",
            (kw.get("area"), kw.get("website"), kw.get("booking_url"),
             kw.get("stars"), kw.get("est_rooms"), kw.get("brand"),
             kw.get("latitude"), kw.get("longitude"), kw.get("xotelo_key"),
             kw.get("booking_engine"), kw.get("review_rating"), kw.get("review_count"),
             kw.get("price_min"), kw.get("price_max"), hid))
        conn.commit()
        return hid
    cur = conn.execute(
        """INSERT INTO hotels(
           name,area,website,booking_url,stars,est_rooms,brand,latitude,longitude,
           xotelo_key,booking_engine,review_rating,review_count,price_min,price_max,deal_stage,created)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (kw.get("name"), kw.get("area"), kw.get("website"), kw.get("booking_url"),
         kw.get("stars"), kw.get("est_rooms"), kw.get("brand", "independent"),
         kw.get("latitude"), kw.get("longitude"), kw.get("xotelo_key"),
         kw.get("booking_engine", "Direct / SynXis"), kw.get("review_rating"),
         kw.get("review_count"), kw.get("price_min"), kw.get("price_max"),
         kw.get("deal_stage", "new"), time.time()))
    conn.commit()
    return cur.lastrowid


def add_contact(conn, hotel_id, kind, value, context="", confidence=0.85):
    clean = normalize_contact_value(kind, value)
    if not clean:
        return False
    try:
        before = conn.total_changes
        conn.execute(
            "INSERT OR IGNORE INTO contacts(hotel_id,kind,value,context,confidence,found_at)"
            " VALUES(?,?,?,?,?,?)", (hotel_id, kind, clean, context, confidence, time.time()))
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
    """Most recent nightly price per hotel, with previous price, timestamps, OTA ladder, and parity status."""
    rows = [dict(r) for r in conn.execute("""
      SELECT h.id AS hotel_id, h.name, h.area, h.stars, h.est_rooms, h.brand,
             h.booking_engine, h.price_min, h.price_max, h.review_rating, h.review_count,
             h.website, h.xotelo_key,
             r1.nightly_price AS price, r1.currency, r1.source, r1.checkin, r1.checkout,
             r1.room_type, r1.ota_json, r1.parity_status, r1.undercut_pct, r1.scraped_at,
             (SELECT r2.nightly_price FROM rates r2
               WHERE r2.hotel_id=h.id AND r2.id < r1.id
               ORDER BY r2.id DESC LIMIT 1) AS prev_price,
             (SELECT r2.scraped_at FROM rates r2
               WHERE r2.hotel_id=h.id AND r2.id < r1.id
               ORDER BY r2.id DESC LIMIT 1) AS prev_scraped_at
      FROM hotels h
      JOIN rates r1 ON r1.id = (
        SELECT id FROM rates WHERE hotel_id=h.id ORDER BY id DESC LIMIT 1)
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
