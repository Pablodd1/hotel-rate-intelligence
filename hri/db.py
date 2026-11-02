"""SQLite storage. Schema is deliberately small and queryable by hand.

Tables
  hotels    – one row per property in the competitive set
  contacts  – people/addresses found on the hotel's own site (the "get the contact" layer)
  rates     – one price observation per hotel per run (source: ota | direct | manual)
  runs      – collector executions (status + stats)
  prospects – hotels scored by "who needs rate intelligence" heuristics
"""
import sqlite3, time

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
  created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY,
  hotel_id INTEGER NOT NULL REFERENCES hotels(id),
  kind TEXT NOT NULL,            -- phone | email | person | address | linkedin
  value TEXT NOT NULL,
  context TEXT,                  -- where it was found: homepage /contact ...
  confidence REAL DEFAULT 0.8,
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
  signals TEXT,                -- JSON list of reasons
  scored_at REAL NOT NULL
);
"""


def open_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_hotel(conn, **kw):
    row = conn.execute("SELECT id FROM hotels WHERE name=?", (kw["name"],)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO hotels(name,area,website,booking_url,stars,est_rooms,brand,latitude,longitude,created)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)",
        (kw.get("name"), kw.get("area"), kw.get("website"), kw.get("booking_url"),
         kw.get("stars"), kw.get("est_rooms"), kw.get("brand", "independent"),
         kw.get("latitude"), kw.get("longitude"), time.time()))
    conn.commit()
    return cur.lastrowid


def add_contact(conn, hotel_id, kind, value, context="", confidence=0.8):
    value = (value or "").strip()
    if not value:
        return False
    try:
        conn.execute(
            "INSERT OR IGNORE INTO contacts(hotel_id,kind,value,context,confidence,found_at)"
            " VALUES(?,?,?,?,?,?)", (hotel_id, kind, value, context, confidence, time.time()))
        conn.commit()
        return True
    except sqlite3.Error:
        return False


def add_rate(conn, hotel_id, run_id, source, checkin, checkout, nightly_price, currency, room_type=None):
    conn.execute(
        "INSERT INTO rates(hotel_id,run_id,source,checkin,checkout,nightly_price,currency,room_type,scraped_at)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (hotel_id, run_id, source, checkin, checkout, nightly_price, currency, room_type, time.time()))
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
    """Most recent nightly price per hotel, with previous price for delta."""
    return [dict(r) for r in conn.execute("""
      SELECT h.id AS hotel_id, h.name, h.area, h.stars, h.est_rooms,
             r1.nightly_price AS price, r1.currency, r1.source, r1.checkin, r1.scraped_at,
             (SELECT r2.nightly_price FROM rates r2
               WHERE r2.hotel_id=h.id AND r2.scraped_at < r1.scraped_at
               ORDER BY r2.scraped_at DESC LIMIT 1) AS prev_price
      FROM hotels h
      JOIN rates r1 ON r1.id = (
        SELECT id FROM rates WHERE hotel_id=h.id ORDER BY scraped_at DESC LIMIT 1)
      ORDER BY h.name""")]


def count_contacts(conn, hotel_id):
    return conn.execute("SELECT COUNT(*) c FROM contacts WHERE hotel_id=?", (hotel_id,)).fetchone()["c"]
