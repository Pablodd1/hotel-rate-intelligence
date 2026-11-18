#!/usr/bin/env python3
"""End-to-End ("Twin") Smoke Test for Hotel Rate Intelligence (`scripts/e2e_smoke_test.py`).

Verifies:
  1. SQLite zero-hallucination data hygiene (0 synthetic rates, 0 fake roles, 100% MX-valid emails, 100% cited leaders).
  2. Live HTTP server endpoints (`127.0.0.1:8317`) including `/`, `/api/summary`, `/api/hotels`, `/api/leads`,
     `/api/outreach`, `/api/market-research`, `/api/calls`, `/api/config`, and `/audit?hotel_id=1`.
  3. Clean UI guarantee (`HRI GlassV4` & `gemini-2.5-flash-lite` absent from `dashboard/index.html`).
  4. Dynamic pricing tests (`?price=79`, `99`, `199`).
  5. Safe dry-run 4-channel outbound (`email`, `sms`, `whatsapp`, `voice`) + opt-out guard + cleanup.
  6. Honest courtesy call queuing (`queued_awaiting_voice_key`, `reported_occupancy_pct is None`) + manual call round-trip + cleanup.
  7. Serverless WSGI entrypoint (`serverless_app.app`) parity check.
"""
import io
import json
import os
import sys
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from hri import config as cfgmod, db as dbmod
from hri.hotel_sites import verify_email_mx


def _http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _http_post(url, payload, headers=None):
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=hdrs,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw}


def main():
    cfg = cfgmod.load()
    base = f"http://{cfg['dashboard']['host']}:{cfg['dashboard']['port']}"
    db_path = os.path.join(ROOT, cfg["database"]) if not os.path.isabs(cfg["database"]) else cfg["database"]
    conn = dbmod.open_db(db_path)

    print("=== 1. DATABASE ZERO-HALLUCINATION HYGIENE ===")
    bad_rates = conn.execute(
        "SELECT COUNT(*) c FROM rates WHERE source IN ('market-calibrated','calibrated') OR nightly_price IS NULL"
    ).fetchone()["c"]
    assert bad_rates == 0, f"Found {bad_rates} synthetic/null rate rows"

    fake_roles = conn.execute(
        "SELECT COUNT(*) c FROM contacts WHERE kind='person' AND context='executive-target'"
    ).fetchone()["c"]
    assert fake_roles == 0, f"Found {fake_roles} fake executive-target role rows"

    uncited_leaders = conn.execute(
        "SELECT COUNT(*) c FROM contacts WHERE kind='person' AND (source_url IS NULL OR source_url='')"
    ).fetchone()["c"]
    assert uncited_leaders == 0, f"Found {uncited_leaders} uncited person rows"

    fake_calls = conn.execute(
        "SELECT COUNT(*) c FROM call_logs WHERE status='recorded_verified'"
    ).fetchone()["c"]
    assert fake_calls == 0, f"Found {fake_calls} synthetic recorded_verified seed calls"

    email_rows = conn.execute("SELECT value, verified_status FROM contacts WHERE kind='email'").fetchall()
    for er in email_rows:
        assert er["verified_status"] == "mx_verified", f"Unverified email status: {er['value']} ({er['verified_status']})"
        assert verify_email_mx(er["value"]), f"Email failed live MX check: {er['value']}"

    hotel_cnt = conn.execute("SELECT COUNT(*) c FROM hotels").fetchone()["c"]
    live_cnt = conn.execute("SELECT COUNT(DISTINCT hotel_id) c FROM rates WHERE nightly_price IS NOT NULL").fetchone()["c"]
    leader_cnt = conn.execute("SELECT COUNT(DISTINCT hotel_id) c FROM contacts WHERE kind='person'").fetchone()["c"]
    phone_cnt = conn.execute("SELECT COUNT(DISTINCT hotel_id) c FROM contacts WHERE kind='phone'").fetchone()["c"]
    print(f"  OK: hotels={hotel_cnt}, live_quoted={live_cnt}, named_leaders={leader_cnt}, mx_emails={len(email_rows)}, phones={phone_cnt}, bad_rows=0")
    assert hotel_cnt >= 35, f"Expected >=35 hotels, got {hotel_cnt}"
    assert live_cnt >= 25, f"Expected >=25 live quoted hotels, got {live_cnt}"
    assert leader_cnt >= 20, f"Expected >=20 cited decision-makers, got {leader_cnt}"

    print("=== 2. LIVE HTTP SERVER, 3-PORTAL SEPARATION & CLEAN HTML CHECKS ===")
    for p_url in ("/", "/website", "/portal", "/mission-control", "/index.html"):
        st, p_html = _http_get(base + p_url)
        assert st == 200, f"{p_url} returned {st}"
        assert "HRI GlassV4" not in p_html, f"Found forbidden string 'HRI GlassV4' in {p_url}"
        assert "gemini-2.5-flash-lite" not in p_html, f"Found forbidden model clutter in {p_url}"

    st_mc, mc_html = _http_get(base + "/mission-control")
    assert 'id="tab-leads"' in mc_html and 'id="tbtn-leads"' in mc_html, "Missing Leads & Outbound tab in Mission Control"

    for ep in ("/api/public/landing", "/api/summary", "/api/hotels", "/api/leads", "/api/outreach", "/api/market-research", "/api/calls", "/api/config"):
        st, body = _http_get(base + ep)
        assert st == 200, f"{ep} returned HTTP {st}"
        data = json.loads(body)
        assert isinstance(data, dict), f"{ep} did not return JSON object"

    st, audit_html = _http_get(base + "/audit?hotel_id=1")
    assert st == 200 and "<html" in audit_html.lower()
    print("  OK: All 3 separated portals (/website, /portal, /mission-control) & GET endpoints 200 OK with zero clutter strings")

    print("=== 2B. TIER LADDER ($0 FREE -> $99 CORE -> $199 PRO), TENANT ISOLATION & ADMIN MISSION CONTROL ===")
    _, pub_raw = _http_get(base + "/api/public/landing")
    pub_json = json.loads(pub_raw)
    tier_prices = [t["monthly_price"] for t in pub_json.get("tiers", [])]
    assert tier_prices == [0, 99, 199, 399], f"Expected tiers [0, 99, 199, 399], got {tier_prices}"

    # Verify Mock Demo Client #1 (avalon / demo1234) login & strict comp-set isolation
    st_cl, cl_login = _http_post(base + "/api/client/login", {"username": "avalon", "password": "demo1234"})
    assert st_cl == 200 and cl_login.get("ok"), f"Demo client login failed: {cl_login}"
    cl_token = cl_login["token"]
    assigned_ids = set(cl_login["account"]["assigned_hotel_ids"])
    assert 1 < len(assigned_ids) <= 12, f"Expected isolated comp-set (2..12 hotels), got {len(assigned_ids)}"

    st_p, cl_portal_raw = _http_get(base + "/api/client/portal", headers={"X-Client-Token": cl_token})
    cl_portal = json.loads(cl_portal_raw)
    assert st_p == 200 and cl_portal.get("isolated_tenant") is True
    assert len(cl_portal["comp_set"]) == len(assigned_ids)

    # Verify Free ($0) Tier preview caps comp-set to 4 properties (primary + 3 neighbors)
    _, free_portal_raw = _http_get(base + "/api/client/portal?preview_tier=free", headers={"X-Client-Token": cl_token})
    free_portal = json.loads(free_portal_raw)
    assert len(free_portal["comp_set"]) <= 4 and free_portal["active_tier"]["monthly_price"] == 0

    # Verify Cross-Tenant Isolation Guard: tagging an unassigned hotel MUST return 403 Forbidden
    unassigned_row = conn.execute(
        f"SELECT id FROM hotels WHERE id NOT IN ({','.join(map(str, assigned_ids))}) LIMIT 1"
    ).fetchone()
    assert unassigned_row is not None
    st_forbid, forbid_res = _http_post(
        base + "/api/client/tags",
        {"hotel_id": unassigned_row["id"], "tag": "Unauthorized Cross-Tenant Tag"},
        headers={"X-Client-Token": cl_token},
    )
    assert st_forbid == 403 and forbid_res.get("forbidden") is True, f"Expected 403 cross-tenant block, got {st_forbid}: {forbid_res}"

    # Verify Self-Serve Free Registration + cleanup
    st_reg, reg_res = _http_post(base + "/api/accounts/register", {
        "primary_hotel_id": unassigned_row["id"],
        "tier": "free",
        "username": "smoketestfree",
        "password": "smoke1234",
        "email": "smoke@testmiamihotel.com",
    })
    assert st_reg == 200 and reg_res.get("ok") and reg_res["account"]["monthly_price"] == 0
    conn.execute("DELETE FROM hotel_tags WHERE account_id=?", (reg_res["account"]["id"],))
    conn.execute("DELETE FROM client_accounts WHERE id=?", (reg_res["account"]["id"],))
    conn.commit()

    # Verify Administrator Mission Control Auth Gate & Overview
    st_unauth_mc, _ = _http_get(base + "/api/admin/overview")
    assert st_unauth_mc == 401, f"Expected 401 on unauthenticated /api/admin/overview, got {st_unauth_mc}"
    st_adm, adm_login = _http_post(base + "/api/admin/login", {"username": "jasmel", "password": "admin305"})
    assert st_adm == 200 and adm_login.get("ok"), f"Admin login failed: {adm_login}"
    st_mc_ov, mc_ov_raw = _http_get(base + "/api/admin/overview", headers={"X-Admin-Token": adm_login["token"]})
    mc_ov = json.loads(mc_ov_raw)
    assert st_mc_ov == 200 and mc_ov.get("ok") and len(mc_ov.get("accounts", [])) >= 3 and len(mc_ov.get("campaigns", [])) >= 10
    print(f"  OK: Tier ladder {tier_prices}, Demo #1 isolation ({len(assigned_ids)} hotels, 403 cross-tenant block), Free signup & Admin Mission Control verified")

    print("=== 3. FLEXIBLE PRICING EXPERIMENT (?price=79 / 99 / 199) ===")
    _, l79 = _http_get(base + "/api/leads?price=79")
    _, l99 = _http_get(base + "/api/leads?price=99")
    _, l199 = _http_get(base + "/api/leads?price=199")
    j79, j99, j199 = json.loads(l79), json.loads(l99), json.loads(l199)
    assert j79["summary"]["price_monthly"] == 79 and j79["summary"]["projected_30_mrr"] == 79 * 30
    assert j99["summary"]["price_monthly"] == 99 and j99["summary"]["projected_30_mrr"] == 99 * 30
    assert j199["summary"]["price_monthly"] == 199 and j199["summary"]["projected_30_mrr"] == 199 * 30
    target_lead = next((x for x in j99["leads"] if x.get("email") and x.get("phone")), None)
    assert target_lead is not None, "Need at least 1 lead with both MX email and phone"
    hid = target_lead["hotel_id"]
    roi79 = next(x["roi_multiple"] for x in j79["leads"] if x["hotel_id"] == hid)
    roi99 = next(x["roi_multiple"] for x in j99["leads"] if x["hotel_id"] == hid)
    roi199 = next(x["roi_multiple"] for x in j199["leads"] if x["hotel_id"] == hid)
    assert roi79 > roi99 > roi199, f"Expected descending ROI multiple with higher price: {roi79}, {roi99}, {roi199}"
    print(f"  OK: Dynamic pricing math verified on hotel #{hid} ({target_lead['short_name']}): ROI {roi79}x ($79) -> {roi99}x ($99) -> {roi199}x ($199)")

    print("=== 4. MULTI-CHANNEL OUTBOUND DRY-RUN, DEEP LINKS & OPT-OUT GUARD ===")
    created_log_ids = []
    expected_prefix = {"email": "mailto:", "sms": "sms:", "whatsapp": "https://wa.me/", "voice": "tel:"}
    for ch, pref in expected_prefix.items():
        st, resp = _http_post(base + "/api/outreach/send", {"hotel_id": hid, "channel": ch, "price_monthly": 99, "mode": "dry_run"})
        assert st == 200 and resp.get("ok"), f"{ch} outreach failed: {resp}"
        assert resp.get("status") != "sent_live", f"Unexpected sent_live without live API keys on {ch}"
        assert (resp.get("deep_link") or "").startswith(pref), f"Missing {pref} deep link: {resp.get('deep_link')}"
        if resp.get("log_id"):
            created_log_ids.append(resp["log_id"])

    test_opt_email = target_lead["email"]
    st, ores = _http_post(base + "/api/opt-out", {"value": test_opt_email, "channel": "email", "reason": "smoke_test"})
    assert st == 200 and ores.get("ok")
    st, blk = _http_post(base + "/api/outreach/send", {"hotel_id": hid, "channel": "email", "price_monthly": 99, "mode": "dry_run"})
    assert blk.get("status") == "opted_out", f"Opt-out guard failed: {blk}"

    # Clean temporary smoke-test rows from outreach_log & do_not_contact
    conn.execute("DELETE FROM do_not_contact WHERE lower(value)=?", (test_opt_email.lower(),))
    if created_log_ids:
        conn.execute(f"DELETE FROM outreach_log WHERE id IN ({','.join('?'*len(created_log_ids))})", created_log_ids)
    conn.execute("DELETE FROM outreach_log WHERE recipient=? AND status='opted_out'", (test_opt_email,))
    conn.commit()
    print(f"  OK: All 4 channels ({', '.join(expected_prefix)}) queued honestly with native deep links + opt-out guard verified")

    print("=== 5. COURTESY CALL HONESTY & MANUAL LOGGING ===")
    st, call_q = _http_post(base + "/api/calls", {"hotel_id": hid, "caller_mode": "Smoke Auto-Caller"})
    assert st == 200 and call_q.get("ok"), f"/api/calls queue failed: {call_q}"
    assert call_q.get("status") == "queued_awaiting_voice_key", f"Unexpected call status: {call_q}"
    assert call_q.get("reported_occupancy_pct") is None, f"Call must not fabricate occupancy: {call_q}"

    st, call_m = _http_post(base + "/api/calls", {
        "hotel_id": hid,
        "caller_mode": "Recorded Desk Courtesy Call",
        "reported_occupancy_pct": 81,
        "rooms_left": 7,
        "quoted_walkin_rate": 249,
        "transcript": "Smoke-test manual night audit entry",
    })
    assert st == 200 and call_m.get("ok") and call_m.get("status") == "verified_manual_call"
    conn.execute("DELETE FROM call_logs WHERE id IN (?, ?)", (call_q["call_id"], call_m["call_id"]))
    conn.commit()
    print("  OK: Courtesy call queued without fake occupancy & verified manual call round-trip succeeded")

    print("=== 6. SERVERLESS WSGI PARITY CHECK ===")
    import serverless_app

    def _call_wsgi(path_qs):
        p, _, qs = path_qs.partition("?")
        env = {"REQUEST_METHOD": "GET", "PATH_INFO": p, "QUERY_STRING": qs, "RAW_URI": path_qs}
        captured = {}

        def start_resp(status, headers):
            captured["status"] = status

        body = b"".join(serverless_app.app(env, start_resp))
        return captured["status"], body.decode("utf-8", errors="replace")

    s_unauth, _ = _call_wsgi("/api/summary")
    assert s_unauth.startswith("401"), f"Expected 401 without ?k=, got {s_unauth}"
    auth_k = serverless_app._KEY
    for wp in ("/", "/api/summary", "/api/hotels", "/api/leads", "/api/market-research"):
        s_ok, b_ok = _call_wsgi(f"{wp}?k={auth_k}")
        assert s_ok.startswith("200"), f"WSGI {wp} returned {s_ok}: {b_ok[:120]}"
    print("  OK: Serverless WSGI auth + 200 responses verified")

    print("=== 7. 49-HOTEL DEMO ISOLATION, LIVE AUDITOR + GRAPHICS, CLOSER CHATBOT & CALLBACKS ===")
    st_dh, dh_raw = _http_get(base + "/api/client/portal?demo_hotel=38")
    assert st_dh == 200, f"/api/client/portal?demo_hotel=38 failed: {st_dh}"
    dh_data = json.loads(dh_raw)
    assert dh_data.get("isolated_tenant") is True and dh_data["primary_hotel"]["id"] == 38, f"Expected isolated hotel #38, got {dh_data.get('primary_hotel')}"
    assert "<svg" in ((dh_data.get("graphics") or {}).get("ota_ladder_svg") or ""), "Missing OTA SVG chart in client portal"

    st_aud38, aud38_html = _http_get(base + "/audit?hotel_id=38")
    assert st_aud38 == 200 and "<svg" in aud38_html and "DECISION-MAKING ASSISTANT" in aud38_html

    st_ar, ar_res = _http_post(base + "/api/audit/run", {"hotel_id": 38, "force_scrape": False})
    assert st_ar == 200 and ar_res.get("ok"), f"/api/audit/run failed: {ar_res}"
    assert ar_res["form_autofill"]["hotel_id"] == 38
    assert "<svg" in ar_res["graphics"]["ota_ladder_svg"]
    assert ar_res["decision_assistant"]["recommended_bar"] > 0

    st_ac, ac_res = _http_post(base + "/api/audit/call", {"hotel_id": 38})
    assert st_ac == 200 and ac_res.get("ok"), f"/api/audit/call failed: {ac_res}"

    st_ae, ae_res = _http_post(base + "/api/audit/send-email", {"hotel_id": 38, "mode": "dry_run"})
    assert st_ae == 200 and ae_res.get("ok"), f"/api/audit/send-email failed: {ae_res}"
    assert "DECISION-MAKING ASSISTANT" in (ae_res.get("html_preview") or "")

    st_ch, ch_res = _http_post(base + "/api/public/chat", {"message": "Avalon Hotel", "hotel_id": 38})
    assert st_ch == 200 and ch_res.get("ok") and ch_res.get("reply"), f"/api/public/chat failed: {ch_res}"
    assert len(ch_res.get("actions") or []) >= 1

    st_cb, cb_res = _http_post(base + "/api/public/callback", {"phone": "305-555-0199", "name": "Smoke Test GM", "hotel_id": 38})
    assert st_cb == 200 and cb_res.get("ok") and cb_res.get("phone_e164") == "+13055550199", f"/api/public/callback failed: {cb_res}"

    if ac_res.get("call_id"):
        conn.execute("DELETE FROM call_logs WHERE id=?", (ac_res["call_id"],))
    for res_row in (ae_res.get("results") or []):
        if res_row.get("log_id"):
            conn.execute("DELETE FROM outreach_log WHERE id=?", (res_row["log_id"],))
    conn.execute("DELETE FROM call_logs WHERE phone_dialed=?", ("+13055550199",))
    conn.execute("DELETE FROM outreach_log WHERE recipient=? AND offer_label='Instant Callback Lead'", ("+13055550199",))
    conn.commit()
    print("  OK: /portal?demo_hotel=38, /audit SVG, /api/audit/{run,call,send-email}, /api/public/{chat,callback} verified!")

    conn.close()
    print("\nALL E2E SMOKE TESTS PASSED!")


if __name__ == "__main__":
    main()
