"""The collector — one run = contacts + best-effort rates + prospect re-score.

Cron it daily:
  0 6 * * * cd /path/to/hotel-rate-intelligence && python3 run.py collect
"""
import random, time, traceback

from . import db as dbmod
from .hotel_sites import scrape_hotel_contacts
from .rate_engine import scrape_direct_rate
from .prospects import score_all


def run_collect(cfg, log=print):
    conn = dbmod.open_db(cfg["database"])
    run_id = dbmod.new_run(conn, mode="collect")
    hotels = [dict(r) for r in conn.execute(
        "SELECT * FROM hotels ORDER BY id LIMIT ?", (cfg["collector"]["max_hotels_per_run"],))]
    attempted = ok = contacts_new = rates_new = 0
    notes = []

    stay = cfg["stay"]
    from datetime import date, timedelta
    checkin = (date.today() + timedelta(days=stay["checkin_days_out"])).isoformat()
    checkout = (date.today() + timedelta(days=stay["checkin_days_out"] + stay["nights"])).isoformat()

    for h in hotels:
        attempted += 1
        try:
            found = scrape_hotel_contacts(h, cfg, log)
            added = 0
            for kind, pairs in found.items():
                for value, ctx in pairs:
                    before = conn.total_changes
                    if dbmod.add_contact(conn, h["id"], kind, value, ctx):
                        added += 1
            contacts_new += added

            price, cur, room = scrape_direct_rate(h, cfg, log=lambda s: log("    " + s))
            if price:
                dbmod.add_rate(conn, h["id"], run_id, "direct", checkin, checkout, price, cur or cfg["currency"], room)
                rates_new += 1
                log(f"    ✓ rate ${price}/{cur or cfg['currency']} ({room or 'std'})")
            ok += 1
        except Exception:
            notes.append(f"{h['name']}: {traceback.format_exc(limit=1).strip().splitlines()[-1][:120]}")
        time.sleep(random.uniform(*cfg["collector"]["polite_delay_sec"]))

    score_all(conn, log)
    status = "ok" if ok else "empty"
    dbmod.finish_run(conn, run_id, status=status, hotels_attempted=attempted,
                     hotels_ok=ok, contacts_new=contacts_new, rates_new=rates_new,
                     notes=" | ".join(notes))
    conn.close()
    log(f"run #{run_id}: {ok}/{attempted} hotels, +{contacts_new} contacts, +{rates_new} rates")
    return run_id
