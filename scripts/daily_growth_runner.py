#!/usr/bin/env python3
"""Warmup-Safe Daily Growth, Live Rate Sync & Wave Outreach Runner (`scripts/daily_growth_runner.py`).

Runs safely either manually or from the scheduled 6:00 AM daily automation:
  1. Refreshes live Xotelo + JSON-LD rates across Miami (--collect).
  2. Refreshes static snapshot JSONs (--snapshot).
  3. Checks warmup window (>= 19 hours since last live email wave) before sending
     the next Wave (10-12 uncontacted verified boutique leads) when --send-wave is passed.
  4. Sends a single 2-sentence Day-3 follow-up (>= 68 hours after touch 1) for
     non-opted-out contacted hotels when --followup is passed.
  5. Emails a concise daily digest to the owner inbox when live actions occur.
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from hri import audit_engine, collector, config as cfgmod, db as dbmod, outreach_engine
from hri.hotel_sites import verify_email_mx
from scripts import snapshot as snapshot_mod

MIN_HOURS_BETWEEN_WAVES = 19.0
FOLLOWUP_MIN_HOURS = 68.0


def _pick_next_wave(conn, limit: int = 12) -> list:
    sent_ids = {
        int(r["hotel_id"])
        for r in conn.execute("SELECT DISTINCT hotel_id FROM outreach_log WHERE status='sent_live'").fetchall()
    }
    leads = outreach_engine.list_verified_leads(conn, price_monthly=99).get("leads") or []
    eligible = []
    for ld in leads:
        hid = int(ld["hotel_id"])
        em = (ld.get("email") or "").strip().lower()
        if hid in sent_ids or not em or em.startswith("careers@") or not ld.get("price"):
            continue
        if outreach_engine._is_opted_out(conn, em):
            continue
        eligible.append(ld)

    eligible.sort(key=lambda x: (
        0 if (x.get("est_rooms") or 99) <= 95 else 1,
        0 if x.get("parity_status") == "UNDERCUT" else 1,
        0 if x.get("person_name") else 1,
        -abs(float(x.get("undercut_pct") or 0.0)),
    ))
    return eligible[:limit]


def _pick_day3_followups(conn, limit: int = 10) -> list:
    now = time.time()
    rows = conn.execute(
        """SELECT o.hotel_id, o.recipient, o.person_name, MIN(o.created_at) AS first_sent,
                  h.name AS hotel_name, h.deal_stage
           FROM outreach_log o
           JOIN hotels h ON h.id = o.hotel_id
           WHERE o.channel='email' AND o.status='sent_live'
           GROUP BY o.hotel_id, o.recipient"""
    ).fetchall()
    candidates = []
    for r in rows:
        if r["deal_stage"] in ("won", "lost", "opted_out"):
            continue
        age_hrs = (now - float(r["first_sent"] or 0)) / 3600.0
        if age_hrs < FOLLOWUP_MIN_HOURS:
            continue
        if outreach_engine._is_opted_out(conn, r["recipient"]):
            continue
        already_fu = conn.execute(
            "SELECT 1 FROM outreach_log WHERE hotel_id=? AND offer_label='Day-3 Follow-Up' LIMIT 1",
            (r["hotel_id"],),
        ).fetchone()
        if already_fu:
            continue
        candidates.append(dict(r))
    return candidates[:limit]


def main():
    ap = argparse.ArgumentParser(description="HotelRateIntel warmup-safe daily growth runner")
    ap.add_argument("--collect", action="store_true", help="Scrape fresh Xotelo rates before outreach")
    ap.add_argument("--send-wave", action="store_true", help="Send next warmup-safe outreach wave")
    ap.add_argument("--followup", action="store_true", help="Send Day-3 follow-ups if >=68h elapsed")
    ap.add_argument("--snapshot", action="store_true", help="Regenerate api/snapshot_*.json")
    ap.add_argument("--wave-size", type=int, default=12, help="Max properties per daily wave")
    ap.add_argument("--dry-run", action="store_true", help="Preview targets without sending live emails")
    ap.add_argument("--email-digest", action="store_true", help="Email daily summary to owner inbox")
    args = ap.parse_args()

    cfg = cfgmod.load()
    if args.collect:
        collector.run_collect(cfg, crawl_sites=False, log=print)

    conn = dbmod.open_db(cfg["database"])
    now = time.time()
    last_live = conn.execute("SELECT MAX(created_at) AS ts FROM outreach_log WHERE status='sent_live'").fetchone()
    hrs_since_last = ((now - float(last_live["ts"])) / 3600.0) if (last_live and last_live["ts"]) else 999.0

    wave_targets = _pick_next_wave(conn, limit=max(1, min(20, args.wave_size)))
    fu_targets = _pick_day3_followups(conn, limit=10)

    summary_lines = [
        f"HOURS_SINCE_LAST_LIVE_SEND: {hrs_since_last:.1f}h (min required={MIN_HOURS_BETWEEN_WAVES:.1f}h)",
        f"ELIGIBLE_NEXT_WAVE: {len(wave_targets)} hotels",
        f"ELIGIBLE_DAY3_FOLLOWUPS: {len(fu_targets)} hotels",
    ]
    for ld in wave_targets:
        summary_lines.append(
            f"  WAVE_TARGET #{ld['hotel_id']:2d} {ld['name']} -> {ld['email']} ({ld.get('parity_status')} {ld.get('undercut_pct')}%)"
        )

    sent_wave = []
    sent_fu = []

    if args.send_wave:
        if hrs_since_last < MIN_HOURS_BETWEEN_WAVES:
            summary_lines.append(
                f"SKIPPED_WAVE_WARMUP_GUARD: only {hrs_since_last:.1f}h elapsed since last batch (wait >= {MIN_HOURS_BETWEEN_WAVES:.0f}h)"
            )
        elif args.dry_run:
            summary_lines.append(f"DRY_RUN_WAVE: would send to {len(wave_targets)} hotels")
        else:
            for ld in wave_targets:
                res = audit_engine.send_audit_email_to_leaders(
                    conn, cfg, {"hotel_id": ld["hotel_id"], "recipients": [ld["email"]], "mode": "live"}
                )
                first = (res.get("results") or [{}])[0]
                if first.get("status") == "sent_live":
                    sent_wave.append(f"#{ld['hotel_id']} {ld['name']} ({first.get('message_id')})")
                    conn.execute(
                        "UPDATE marketing_campaigns SET approval_status='dispatched', dispatched_at=? WHERE hotel_id=? AND channel='email'",
                        (time.time(), ld["hotel_id"]),
                    )
                time.sleep(0.75)
            conn.commit()
            summary_lines.append(f"WAVE_SENT_LIVE: {len(sent_wave)}/{len(wave_targets)}")

    if args.followup:
        if args.dry_run:
            summary_lines.append(f"DRY_RUN_FOLLOWUPS: {len(fu_targets)} eligible")
        else:
            base_url = (cfg.get("outreach") or {}).get("app_base_url") or "https://hotelrateintel.com"
            for cand in fu_targets:
                em = cand["recipient"]
                if not verify_email_mx(em):
                    continue
                short_h = cand["hotel_name"].split(",")[0].strip()
                subj = f"re: {short_h.lower()} private demo link"
                demo_link = f"{base_url.rstrip('/')}/portal?demo_hotel={cand['hotel_id']}"
                body = (
                    f"Hi {short_h} Reservations Team,\n\n"
                    f"Quick follow-up in case yesterday's OTA parity graphic got buried — your private 1-click rate panel is still live here: {demo_link}.\n\n"
                    f"Want me to turn on the free 6:00 AM daily rate brief for this week? Just reply yes and I'll activate it.\n\n"
                    f"Best,\nJasmel Acosta · North Miami, FL 33161 (Reply STOP to opt out)"
                )
                sres = outreach_engine._send_live_email(cfg, em, subj, body)
                st = "sent_live" if sres.get("ok") else "failed"
                conn.execute(
                    """INSERT INTO outreach_log(hotel_id,channel,recipient,person_name,offer_price_monthly,offer_label,
                       subject,body,provider,status,provider_message_id,error_detail,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (cand["hotel_id"], "email", em, f"{short_h} Team", 99, "Day-3 Follow-Up",
                     subj, body, sres.get("provider", "resend"), st, sres.get("msg_id", ""), sres.get("error", ""), time.time()),
                )
                if sres.get("ok"):
                    sent_fu.append(f"#{cand['hotel_id']} {short_h} ({sres.get('msg_id')})")
                time.sleep(0.75)
            conn.commit()
            summary_lines.append(f"FOLLOWUPS_SENT_LIVE: {len(sent_fu)}/{len(fu_targets)}")

    if args.snapshot:
        snapshot_mod.main()

    out_text = "\n".join(summary_lines)
    print(out_text)

    if args.email_digest and not args.dry_run and (sent_wave or sent_fu):
        to_owner = ((cfg.get("email_report") or {}).get("to_email") or "jasmelacosta@gmail.com").strip()
        outreach_engine._send_live_email(
            cfg,
            to_owner,
            f"HotelRateIntel Growth Digest: {len(sent_wave)} new waves + {len(sent_fu)} follow-ups sent",
            out_text,
        )

    conn.close()


if __name__ == "__main__":
    main()
