"""The collector — one run = contacts + multi-OTA rate parity + prospect re-score.

Cron it daily:
  0 6 * * * cd /path/to/hotel-rate-intelligence && python3 run.py collect
"""
import random, time, traceback
from datetime import date, timedelta

from . import db as dbmod
from .hotel_sites import scrape_hotel_contacts
from .rate_engine import scrape_rate_intelligence, fetch_xotelo_catalog
from .prospects import score_all


def run_collect(cfg, crawl_sites=True, log=print):
    conn = dbmod.open_db(cfg["database"])
    run_id = dbmod.new_run(conn, mode="collect")
    hotels = [dict(r) for r in conn.execute(
        "SELECT * FROM hotels ORDER BY id LIMIT ?", (cfg["collector"]["max_hotels_per_run"],))]
    attempted = ok = contacts_new = rates_new = 0
    notes = []

    stay = cfg["stay"]
    checkin_prev = (date.today() + timedelta(days=max(7, stay["checkin_days_out"] - 14))).isoformat()
    checkout_prev = (date.today() + timedelta(days=max(7, stay["checkin_days_out"] - 14) + stay["nights"])).isoformat()
    checkin = (date.today() + timedelta(days=stay["checkin_days_out"])).isoformat()
    checkout = (date.today() + timedelta(days=stay["checkin_days_out"] + stay["nights"])).isoformat()

    # Pre-warm Xotelo Miami Beach catalog once
    fetch_xotelo_catalog()

    for h in hotels:
        attempted += 1
        try:
            if crawl_sites and cfg.get("sources", {}).get("hotel_sites", True):
                found = scrape_hotel_contacts(h, cfg, log)
                added = 0
                for kind, pairs in found.items():
                    for value, ctx in pairs:
                        if dbmod.add_contact(conn, h["id"], kind, value, ctx):
                            added += 1
                contacts_new += added

            # If hotel has no historical baseline rate yet, record the 14-day horizon baseline first
            existing_rates = conn.execute("SELECT COUNT(*) c FROM rates WHERE hotel_id=?", (h["id"],)).fetchone()["c"]
            if existing_rates == 0:
                base_intel = scrape_rate_intelligence(h, cfg, checkin=checkin_prev, checkout=checkout_prev, log=lambda s: None)
                if base_intel.get("direct_price"):
                    dbmod.add_rate(
                        conn, h["id"], run_id, base_intel["source"],
                        checkin_prev, checkout_prev, base_intel["direct_price"],
                        cfg["currency"], base_intel["room_type"],
                        ota_json=base_intel["channels"],
                        parity_status=base_intel["parity_status"],
                        undercut_pct=base_intel["undercut_pct"],
                        scraped_at=time.time() - 86400,
                    )
                    rates_new += 1

            # Capture current 30-day horizon rate & multi-OTA parity ladder
            intel = scrape_rate_intelligence(
                h, cfg, checkin=checkin, checkout=checkout,
                check_jsonld=crawl_sites,
                log=lambda s, hn=h["name"]: log(f"    [OK] {hn}: {s}"))
            if intel.get("direct_price"):
                dbmod.add_rate(
                    conn, h["id"], run_id, intel["source"],
                    checkin, checkout, intel["direct_price"],
                    cfg["currency"], intel["room_type"],
                    ota_json=intel["channels"],
                    parity_status=intel["parity_status"],
                    undercut_pct=intel["undercut_pct"],
                )
                rates_new += 1
                dbmod.upsert_hotel(
                    conn, name=h["name"],
                    price_min=intel.get("price_min"),
                    price_max=intel.get("price_max"),
                    review_rating=intel.get("review_rating"),
                    review_count=intel.get("review_count"),
                )
            ok += 1
        except Exception:
            notes.append(f"{h['name']}: {traceback.format_exc(limit=1).strip().splitlines()[-1][:120]}")
        if crawl_sites:
            time.sleep(random.uniform(*cfg["collector"]["polite_delay_sec"]))

    score_all(conn, log)
    status = "ok" if ok else "empty"
    dbmod.finish_run(conn, run_id, status=status, hotels_attempted=attempted,
                     hotels_ok=ok, contacts_new=contacts_new, rates_new=rates_new,
                     notes=" | ".join(notes))
    conn.close()
    log(f"run #{run_id}: {ok}/{attempted} hotels, +{contacts_new} contacts, +{rates_new} rates")
    return run_id
