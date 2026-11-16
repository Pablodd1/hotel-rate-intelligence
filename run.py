#!/usr/bin/env python3
"""Hotel Rate Intelligence — CLI.

  python3 run.py init-db          create schema
  python3 run.py seed             load the 30-hotel Miami Beach competitive set
  python3 run.py collect          contacts + live multi-OTA rates + prospect scoring
  python3 run.py collect --fast   rates + scoring without re-crawling hotel HTML pages
  python3 run.py report           print the daily executive & sales brief
  python3 run.py report --send    also push it to Telegram
  python3 run.py pitch [hotel_id] print personalized call script, SMS & email kit
  python3 run.py send-briefs      generate & dispatch 6:00 AM daily rate briefs to active pilot/client hotels
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

    elif cmd == "hunt-leads":
        from hri.lead_hunter import run_lead_hunter
        quick = "--quick" in sys.argv
        run_lead_hunter(cfg, quick=quick)

    elif cmd == "outreach":
        from hri import db as dbmod
        from hri.outreach_engine import send_or_queue_outreach, get_channel_readiness
        channel = "email"
        tier = "hot"
        price = int((cfg.get("outreach") or {}).get("default_price_monthly") or 99)
        limit = 10
        live = "--live" in sys.argv
        for a in sys.argv[2:]:
            if a.startswith("--channel="):
                channel = a.split("=", 1)[1]
            elif a.startswith("--tier="):
                tier = a.split("=", 1)[1]
            elif a.startswith("--price="):
                price = int(a.split("=", 1)[1])
            elif a.startswith("--limit="):
                limit = int(a.split("=", 1)[1])
        conn = dbmod.open_db(cfg["database"])
        if "--status" in sys.argv:
            print(json.dumps(get_channel_readiness(cfg), indent=2))
        else:
            res = send_or_queue_outreach(conn, cfg, {
                "batch": True,
                "channel": channel,
                "tier": tier,
                "price_monthly": price,
                "limit": limit,
                "mode": "live" if live else "dry_run",
            })
            print(json.dumps({k: v for k, v in res.items() if k != "results"}, indent=2))
            for item in res.get("results", []):
                print(f"  [{item.get('status')}] #{item.get('hotel_id')} {item.get('hotel_name')} -> {item.get('recipient')} ({channel})")
        conn.close()

    elif cmd == "market-research":
        from hri import db as dbmod
        from hri.outreach_engine import build_market_research_and_posts
        conn = dbmod.open_db(cfg["database"])
        res = build_market_research_and_posts(conn)
        conn.close()
        print(json.dumps(res, indent=2))

    elif cmd == "launch-status":
        from hri import db as dbmod
        from hri.outreach_engine import get_channel_readiness, list_verified_leads
        conn = dbmod.open_db(cfg["database"])
        leads = list_verified_leads(conn, price_monthly=99)["summary"]
        conn.close()
        print(json.dumps({"leads": leads, "readiness": get_channel_readiness(cfg)}, indent=2))

    elif cmd == "smoke-test":
        import subprocess
        raise SystemExit(subprocess.call([sys.executable, "scripts/e2e_smoke_test.py"]))

    elif cmd == "send-briefs":
        from hri import db as dbmod
        from hri.sales_engine import build_hotel_pitch
        conn = dbmod.open_db(cfg["database"])
        rows = conn.execute(
            "SELECT id, name, deal_stage FROM hotels WHERE deal_stage IN ('pilot_active', 'closed_won') ORDER BY id"
        ).fetchall()
        if not rows:
            rows = conn.execute("SELECT id, name, deal_stage FROM hotels ORDER BY id LIMIT 3").fetchall()
            print("[info] No hotels marked pilot_active/closed_won yet — previewing top 3 properties:\n")
        for r in rows:
            p = build_hotel_pitch(conn, r["id"])
            h = p["hotel"]
            ri = p["rate_intel"]
            ai = p.get("ai_brief") or {}
            otd = p.get("out_the_door") or {}
            print(f"✉ 6:00 AM CLIENT BRIEF → {h['name']} ({h['primary_email']} | {h['primary_phone']})")
            print(f"   Model: {ai.get('model_used')} | Direct BAR: ${ri['direct_bar']} (${otd.get('direct_out_the_door')} Out-the-Door)")
            print(f"   Lowest OTA: {ri['lowest_ota_name']} @ ${ri['lowest_ota_price']} ({ri['undercut_pct']:+.1f}% [{ri['parity_status']}])")
            print(f"   AI Action: {ai.get('gm_executive_memo')}\n")
        conn.close()

    elif cmd == "dashboard":
        from hri.server import serve
        serve(cfg)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
