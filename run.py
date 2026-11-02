#!/usr/bin/env python3
"""Hotel Rate Intelligence — CLI.

  python3 run.py init-db          create schema
  python3 run.py seed             load the Miami Beach competitive set
  python3 run.py collect          contacts + rates + prospect scoring
  python3 run.py report           print the daily brief
  python3 run.py report --send    also push it to Telegram
  python3 run.py dashboard        serve the themed dashboard
"""
import sys

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
        run_collect(cfg)

    elif cmd == "report":
        from hri.report import build_brief, send_telegram
        text = build_brief(cfg["database"], cfg["market"])
        print(text)
        if "--send" in sys.argv and send_telegram(cfg, text):
            print("\n[sent to Telegram]")

    elif cmd == "dashboard":
        from hri.server import serve
        serve(cfg)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
