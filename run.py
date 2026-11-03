#!/usr/bin/env python3
"""Hotel Rate Intelligence — CLI.

  python3 run.py init-db          create schema
  python3 run.py seed             load the 30-hotel Miami Beach competitive set
  python3 run.py collect          contacts + live multi-OTA rates + prospect scoring
  python3 run.py collect --fast   rates + scoring without re-crawling hotel HTML pages
  python3 run.py report           print the daily executive & sales brief
  python3 run.py report --send    also push it to Telegram
  python3 run.py pitch [hotel_id] print personalized call script, SMS & email kit
  python3 run.py snapshot         export JSON snapshots to api/ for Vercel deploy
  python3 run.py dashboard        serve the themed 5-tab command center
"""
import json, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from hri.config import load


def main():
    cfg = load()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "init-db":
        from hri import db as dbmod
        dbmod.open_db(cfg["database"]).close()
        print(f"db ready: {cfg['database']}")

    elif cmd == "seed":
        from hri import db as dbmod
        from hri.seed import seed
        conn = dbmod.open_db(cfg["database"])
        seed(conn)
        conn.close()

    elif cmd == "collect":
        from hri.collector import run_collect
        fast = "--fast" in sys.argv
        run_collect(cfg, crawl_sites=not fast)

    elif cmd == "report":
        from hri.report import build_brief, send_telegram
        text = build_brief(cfg["database"], cfg["market"])
        print(text)
        if "--send" in sys.argv and send_telegram(cfg, text):
            print("\n[sent to Telegram]")

    elif cmd == "pitch":
        from hri import db as dbmod
        from hri.sales_engine import build_hotel_pitch
        hid = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 4
        conn = dbmod.open_db(cfg["database"])
        pitch = build_hotel_pitch(conn, hid)
        conn.close()
        h = pitch["hotel"]
        ri = pitch["rate_intel"]
        roi = pitch["roi_calculator"]
        cs = pitch["call_script"]
        print(f"=== SALES KIT: {h['name']} ({h['area']} · {h['est_rooms']} rooms · {h['stars']}★) ===")
        print(f"Dial: {h['primary_phone']} | Email: {h['primary_email']} | Target: {h['target_role']}")
        print(f"Rate: ${ri['direct_bar']} BAR vs ${ri['lowest_ota_price']} on {ri['lowest_ota_name']} ({ri['undercut_pct']:+.1f}% [{ri['parity_status']}])")
        print(f"Est. Annual Upside: +${roi['total_annual_roi']:,}/yr ({roi['roi_multiple']}x ROI on {roi['recommended_tier']})\n")
        print("--- GATEKEEPER BYPASS ---")
        print(cs["gatekeeper_bypass"])
        print("\n--- 30-SEC GM OPENER ---")
        print(cs["gm_opener_30_sec"])
        print("\n--- SMS #1 ---")
        print(pitch["sms_templates"][0]["text"])
        print("\n--- COLD EMAIL #1 ---")
        print("Subject:", pitch["emails"][0]["subject"])
        print(pitch["emails"][0]["body"])

    elif cmd == "snapshot":
        from scripts.snapshot import main as snap_main
        snap_main()

    elif cmd == "dashboard":
        from hri.server import serve
        serve(cfg)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
