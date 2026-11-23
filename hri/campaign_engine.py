"""Standards-Compliant 20-Email Campaign Engine, Suppression & Deliverability Monitor (`hri/campaign_engine.py`).

ZERO-HALLUCINATION & ANTI-BAN DESIGN:
1. Every email leads with a 2-sentence hospitality psychology hook + plain-English basic explanation
   of our 6:00 AM online rate search across OTAs & neighboring Miami hotels.
2. Every email embeds the clickable 10-second minimalist video poster linking to `https://hotelrateintel.com/#blogs`.
3. Every email carries RFC-8058 `List-Unsubscribe` + `List-Unsubscribe-Post: List-Unsubscribe=One-Click`
   headers + CAN-SPAM North Miami physical address.
4. Enforces hard suppression on hard bounces, 2x soft bounces, spam complaints/blocks (domain-wide),
   unsubscribes, replied threads, non-Miami sister domains, 48-hour minimum spacing, and safe daily caps.

CLI usage:
  python -m hri.campaign_engine status
  python -m hri.campaign_engine clean-contacts
  python -m hri.campaign_engine suppress bad@hotel.com --reason hard_bounce
  python -m hri.campaign_engine send --step 1 --test-to jasmelacosta@gmail.com
  python -m hri.campaign_engine send --step 1 --dry-run --limit 15
  python -m hri.campaign_engine send --step 1 --live --limit 15
"""
import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config as cfgmod
from . import db as dbmod
from .hotel_sites import verify_email_mx

VIDEO_POSTER_URL = "https://hotelrateintel.com/assets/hri_10s_poster.png"
BLOGS_VIDEO_LINK = "https://hotelrateintel.com/#blogs"
FROM_EMAIL = "Jasmel Acosta · HotelRateIntel <jasmel@hotelrateintel.com>"
REPLY_TO = "jasmelacosta@gmail.com"
MIN_SPACING_SEC = 46 * 3600  # 46h floor for every-2-days cadence

# Non-Miami sister/noise email substrings to never send Miami hotel campaigns to
NON_MIAMI_NOISE_PATTERNS = (
    "palihotelsf", "palihotelseattle", "palihotelculvercity", "palihotelhlwd",
    "palihotelsd", "palihotelwestwood", "palihousesb", "palihousetampa",
    "palihousewh", "arrivehotels", "hotellilibh", "lpp8th", "lppbrentwood",
    "lpplaguna", "lppocean", "lppsthelena", "silverlakepi", "saintjamesfrenchdiner",
    "cavalierresortvb", "purplepr.com", "hr@", "careers@", "press@", "pr@", "boats@",
    "dining@", "restaurant@", "membership@", "customer.svc@marriott.com",
)

# All 20 distinct, psychology-first, plain-English emails (every 2 days = 40-day sequence)
CAMPAIGN_20_STEPS = [
    {
        "step": 1, "day": 1, "target_role": "GM / Owner", "dept_filter": ("gm_executive", "general_info", "reservations"),
        "subject": "{short_name} morning rate check",
        "trigger": "Loss Aversion + Plain-English Basic Search",
        "hook": "A guest searches {hotel_name} by name on Google, sees an OTA listing $18–$30 below your own website, and books there — costing you 18% commission on a guest who was already yours.",
        "basic": "What HotelRateIntel does in plain English: every morning at 6:00 AM, our software automatically searches Booking.com, Expedia, Agoda, Vio.com, Trip.com, and your competing {area} hotel websites, then places every live room price side-by-side against yours on one calm screen.",
        "table_title": "Why Miami GMs Switch From Manual Tabs & Corporate Shoppers",
        "rows": [
            ("Daily Online Rate Search", "Automatic 6:00 AM scan", "1–2 hrs clicking 15 tabs"),
            ("OTA Undercut Proof (Agoda / Vio)", "Exact channel & $ gap", "Missed until check-in"),
            ("Pricing & Lock-In", "$0 Free / $99 mo-to-mo", "$350–$500+/mo annual lock-in"),
        ],
        "cta": "Watch the 10-Second Walkthrough & Field Guides",
    },
    {
        "step": 2, "day": 3, "target_role": "Reservations Manager", "dept_filter": ("reservations", "general_info"),
        "subject": "{area_lower} suite rates",
        "trigger": "Tab-Fatigue Relief + Suite-vs-Suite Basics",
        "hook": "How many browser tabs did your Reservations desk open this morning just to see what competing {area} hotels charge for a Two-Doubles or Suite tonight?",
        "basic": "HotelRateIntel runs the entire online rate search automatically across OTAs and competitor websites — and compares exact room equivalents only (Suite vs. Suite, Double-Double vs. Double-Double, Single Occ), normalizing rollaways, Miami resort fees, and 14% tax.",
        "table_title": "Built for Real Reservations Desks",
        "rows": [
            ("Exact Room Equivalency", "Suite vs. Suite & DD vs. DD", "Mixes entry Queen vs. Suite"),
            ("Miami Out-the-Door Checkout", "BAR + Resort Fee + 14% Tax", "Headline BAR only"),
            ("Time Spent Checking Rates", "10 seconds at 6:00 AM", "45–68 staff hrs/mo"),
        ],
        "cta": "See Suite-vs-Suite in 10 Seconds",
    },
    {
        "step": 3, "day": 5, "target_role": "Front Desk / MOD / Night Audit", "dept_filter": ("front_office_mod", "night_audit", "general_info"),
        "subject": "11:30 pm front desk",
        "trigger": "Peer Solidarity (20 Years Hospitality)",
        "hook": "Between 11:30 PM and 6:00 AM, half your hotel's real pricing intel disappears onto sticky notes: neighbor walk-in rates, sudden AC/plumbing OOO rooms, and overflow calls.",
        "basic": "First, HotelRateIntel automatically searches OTAs and competing {area} hotel websites so the desk always sees live street rates. Second, it gives MODs and Night Auditors built-in Pre-Audit (11:30 PM) & Post-Audit (3:30 AM) call-around scripts and 1-click neighbor rate-swap emails.",
        "table_title": "Built for Real Front Office & Overnight Shifts",
        "rows": [
            ("Online Competitor Rate Search", "Automatic 1-screen ladder", "Manual searching at desk"),
            ("Pre-Audit & Post-Audit Call Desk", "Built-in scripts & log", "Not offered by any RMS"),
            ("OOO / Housekeeping Holds", "5-sec toggle + #OOO alert", "Lost between shifts"),
        ],
        "cta": "Watch the 10-Second Desk Overview",
    },
    {
        "step": 4, "day": 7, "target_role": "GM / Owner", "dept_filter": ("gm_executive", "general_info", "reservations"),
        "subject": "miami resort fee math",
        "trigger": "Contrast & Framing",
        "hook": "A nearby {area} hotel showing $219 online with a $42 mandatory resort fee is NOT cheaper than your $245 Direct BAR with $0 resort fee — yet generic rate shoppers tell you to cut price.",
        "basic": "HotelRateIntel automatically checks live OTA and competitor hotel prices every morning AND calculates True Out-the-Door checkout totals (BAR + resort fee + rollaway + 14% Miami-Dade tax) so you never panic-discount against a fake headline rate.",
        "table_title": "Headline Rate vs. True Out-the-Door Math",
        "rows": [
            ("Resort Fee Normalization", "Included per competitor", "Hidden in fine print"),
            ("14% Miami Lodging Tax", "Calculated automatically", "Manual calculator"),
            ("Housekeeping Cadence", "Daily vs. On-Request HK", "Never tracked"),
        ],
        "cta": "Watch the 10-Second Walkthrough + Resort Fee Guide",
    },
    {
        "step": 5, "day": 9, "target_role": "Reservations Manager", "dept_filter": ("reservations", "front_office_mod"),
        "subject": "4 ooo rooms tonight",
        "trigger": "Concrete Scene (Compression Math)",
        "hook": "On a 45-room boutique, 38 rooms sold looks like 84% occupancy — until 4 AC or maintenance OOO rooms drop sellable inventory to 41 and push you to 92.7% net compression.",
        "basic": "HotelRateIntel combines live online competitor rate searches with a 5-second OOO / OOS / Housekeeping hold panel that instantly recalculates true net sellable occupancy and recommends BAR lifts or OTA Stop-Sell before you walk a guest.",
        "table_title": "Gross Occupancy vs. True Sellable Yield",
        "rows": [
            ("OOO / OOS / HK Hold Input", "Editable live in 5 seconds", "Assumes 100% sellable"),
            ("AI BAR Guardrails", "Respects your Floor & Ceiling", "Black-box $500+/mo RMS"),
            ("Stop-Sell / CTA Warnings", "Instant before oversell", "Manual front-desk scramble"),
        ],
        "cta": "See OOO → AI Pricing in 10 Seconds",
    },
    {
        "step": 6, "day": 11, "target_role": "GM / Owner", "dept_filter": ("gm_executive", "reservations", "general_info"),
        "subject": "agoda and vio leaks",
        "trigger": "Commission Pain",
        "hook": "Wholesale bedbanks regularly leak static net rates onto Agoda or Vio.com $20 below your direct website — silently siphoning 18%–22% commission from direct brand searchers.",
        "basic": "Every morning at 6:00 AM, HotelRateIntel checks Booking.com, Expedia, Agoda, Vio.com, and Trip.com against your hotel's official website BAR and flags every channel undercutting you with the exact dollar gap.",
        "table_title": "Multi-OTA Parity Protection",
        "rows": [
            ("Bedbank Leak Detection", "Flags Agoda/Vio/FIT daily", "Discovered by guest complaint"),
            ("Direct Website BAR Match", "Live schema & direct check", "OTAs only"),
            ("Setup Time", "Zero PMS IT needed Day 1", "2–6 weeks IT onboarding"),
        ],
        "cta": "Watch 10-Sec Demo & Parity Guide",
    },
    {
        "step": 7, "day": 13, "target_role": "Front Desk / MOD", "dept_filter": ("front_office_mod", "reservations"),
        "subject": "neighbor rate swap emails",
        "trigger": "Effort Reduction",
        "hook": "When a nearby {area} property sells out or shifts walk-in rates, how fast does your desk log it and share it with morning Reservations?",
        "basic": "Alongside automatic daily online rate comparisons across all OTAs and neighbors, HotelRateIntel includes 1-click neighbor courtesy rate-swap email drafts and a shift log so every MOD and Night Auditor leaves clean data for the 6:00 AM huddle.",
        "table_title": "Front Desk Coordination Without Sticky Notes",
        "rows": [
            ("1-Click Rate-Swap Emails", "Pre-drafted for {area}", "Typed manually in Gmail"),
            ("Walk-In BAR & Rooms Left Log", "Saved to property timeline", "Lost at shift change"),
            ("Free Starter Access", "$0/mo forever (3 comps)", "Paid enterprise seats only"),
        ],
        "cta": "Watch the 10-Second Walkthrough",
    },
    {
        "step": 8, "day": 15, "target_role": "GM / Owner", "dept_filter": ("gm_executive", "general_info"),
        "subject": "99 vs 500 rms",
        "trigger": "Price Anchoring",
        "hook": "Enterprise RMS platforms like Atomize start around $500/month and annual contracts lock small boutique hotels in — even though you only need clean daily rates, parity alerts, and practical yield rules.",
        "basic": "HotelRateIntel runs automatic daily online rate comparisons across OTAs and your local {area} comp-set starting at $0 Free Starter and $99/mo Core — strictly month-to-month with zero annual lock-in.",
        "table_title": "2026 Boutique Hotel Pricing Comparison",
        "rows": [
            ("HotelRateIntel Free / Core", "$0 Free / $99 mo-to-mo", "Cancel anytime"),
            ("RoomPriceGenie", "Flat monthly by rooms", "Annual contract required"),
            ("Atomize / Enterprise RMS", "$500+/mo starting base", "Heavy enterprise onboarding"),
        ],
        "cta": "Watch 10-Sec Overview & Pricing Breakdown",
    },
    {
        "step": 9, "day": 17, "target_role": "Reservations Manager", "dept_filter": ("reservations", "sales_groups"),
        "subject": "rollaways and hk cadence",
        "trigger": "Specificity Proof",
        "hook": "Two Miami boutiques both list $260/nt — one allows a $35 rollaway with daily housekeeping, the other is King-only with stayover HK on request. Are you comparing them accurately?",
        "basic": "HotelRateIntel scans live online rates across OTAs and competitor sites every morning and lets Reservations toggle Single/Double/Triple-Quad occupancy, rollaway beds, resort fees, and housekeeping cadence side-by-side.",
        "table_title": "True Apples-to-Apples Room Matching",
        "rows": [
            ("Occupancy Selector", "Single / Double / Quad", "Single base rate only"),
            ("Rollaway Bed Normalized", "+$35/nt toggle built-in", "Ignored by rate shoppers"),
            ("Housekeeping Cadence", "Daily vs. On-Request tag", "Not tracked"),
        ],
        "cta": "See Room Equivalency in 10 Seconds",
    },
    {
        "step": 10, "day": 19, "target_role": "GM / Owner", "dept_filter": ("gm_executive", "reservations", "general_info"),
        "subject": "1-page {area_lower} audit",
        "trigger": "Reciprocity (Free Ready-Made Gift)",
        "hook": "We already built a live, zero-login 1-page rate parity and corridor comparison sheet for {hotel_name} comparing your current BAR against neighboring {area} properties.",
        "basic": "HotelRateIntel automatically checks OTAs and competing Miami hotel websites daily so your team sees exactly where you sit in the corridor — no setup, no credit card, and no software install required to inspect your sheet.",
        "table_title": "What's Inside Your Free 1-Page Audit",
        "rows": [
            ("Live Multi-OTA Ladder", "Direct vs Booking/Agoda/Vio", "Ready right now"),
            ("Assigned {area} Comps", "Side-by-side BAR & spread", "Updated automatically"),
            ("Printable GM PDF", "1 click for morning huddle", "Zero login needed"),
        ],
        "cta": "Watch 10-Sec Walkthrough & Open Audit",
    },
    {
        "step": 11, "day": 21, "target_role": "Front Desk / Night Audit", "dept_filter": ("front_office_mod", "night_audit", "reservations"),
        "subject": "telegram shift alerts",
        "trigger": "Speed & Simplicity",
        "hook": "Instead of burying urgent parity leaks or OOO holds inside noisy group texts, what if your Reservations and MOD team received tagged 6:00 AM briefs straight on Telegram?",
        "basic": "HotelRateIntel searches online competitor and OTA prices automatically and sends clean, tagged alerts (#OOO, #HK, #ParityLeak, #Compression, #NightAudit) to Telegram and email at $0 extra cost.",
        "table_title": "Instant Shift Alerts Included",
        "rows": [
            ("6:00 AM Daily Brief", "Plain-English BAR move", "Complex BI logins"),
            ("Tagged Telegram Alerts", "#OOO #ParityLeak #NightAudit", "Not offered by corporate RMS"),
            ("Cost for Telegram Alerts", "$0 extra (built-in)", "Add-on enterprise fees"),
        ],
        "cta": "Watch the 10-Second Walkthrough",
    },
    {
        "step": 12, "day": 23, "target_role": "GM / Owner", "dept_filter": ("gm_executive", "sales_groups", "reservations"),
        "subject": "art basel and f1 dates",
        "trigger": "Compression Timing (Miami Events)",
        "hook": "During Art Basel, Miami F1, and the Boat Show, waiting 48 hours too long to lift BAR or set a 2-night Min-LOS can cost a 50-room Miami hotel $15,000+ in a single weekend.",
        "basic": "HotelRateIntel combines daily online OTA & competitor price tracking with a Miami Event & Compression Radar so independent hotels spot corridor rate jumps the moment neighbors move.",
        "table_title": "Miami Compression Readiness",
        "rows": [
            ("Miami Event Calendar", "Art Basel, F1, Boat Show", "Generic national averages"),
            ("Neighbor Rate Move Tracking", "Spots +10% jumps at 6 AM", "Found days too late"),
            ("Min-LOS & CTA Signals", "Built into AI Auto-Pricing", "Manual spreadsheets"),
        ],
        "cta": "Watch 10-Sec Walkthrough & Guides",
    },
    {
        "step": 13, "day": 25, "target_role": "Reservations / Revenue", "dept_filter": ("reservations", "gm_executive"),
        "subject": "cloudbeds and mews sync",
        "trigger": "Risk Reversal (2-Way PMS Security)",
        "hook": "Worried about handing write access to your PMS on day one? You don't have to — start with zero-IT public rate monitoring today, then turn on secure 2-way API pushes only when you trust the numbers.",
        "basic": "HotelRateIntel scans public OTAs and hotel websites automatically with zero PMS access, and includes ready-to-connect guardrailed API wire formats for Cloudbeds, Mews, Channex (50+ OTAs), and SiteMinder/SynXis with hard Floor/Ceiling clamps and 1-click rollback.",
        "table_title": "Safe 2-Phase PMS Integration",
        "rows": [
            ("Day 1 Setup", "Zero PMS credentials needed", "Weeks of IT tickets"),
            ("Live Dynamic Push", "Cloudbeds, Mews, Channex, SynXis", "Rigid single-vendor lock"),
            ("Safety Guardrails", "Floor/Ceiling + 1-Click Rollback", "Unchecked auto-changes"),
        ],
        "cta": "Watch 10-Sec Demo & PMS Security Guide",
    },
    {
        "step": 14, "day": 27, "target_role": "GM / Owner", "dept_filter": ("gm_executive", "general_info"),
        "subject": "support local miami",
        "trigger": "In-Group Identity (Local Hotelier)",
        "hook": "Most hotel software companies are based out of state or overseas and have never worked a South Beach check-in rush or a 2:00 AM night audit roll.",
        "basic": "HotelRateIntel is built right here in North Miami from 20 years of luxury hotel & residential hospitality experience — automating your daily online OTA and competitor rate search with bilingual (EN/ES) local support you can text or call directly at (786) 970-8366.",
        "table_title": "Local Miami Partner vs. Overseas SaaS",
        "rows": [
            ("Direct Local Support", "Call/Text Jasmel (786) 970-8366", "Ticket queue & bots"),
            ("Hospitality DNA", "20 yrs luxury Miami hotels", "Tech-only vendors"),
            ("Monthly Terms", "$0 Free / $99 mo-to-mo", "Long-term corporate contracts"),
        ],
        "cta": "Watch Our 10-Second Miami Walkthrough",
    },
    {
        "step": 15, "day": 29, "target_role": "Reservations Manager", "dept_filter": ("reservations", "general_info"),
        "subject": "competitor pricing memory",
        "trigger": "Curiosity Gap",
        "hook": "Do you remember which {area} neighbor dumped rates 18% last Tuesday night — and which one held firm until Friday morning?",
        "basic": "Beyond running your daily 6:00 AM online rate search across OTAs and competitors, HotelRateIntel remembers every competitor's historical rate moves, classifies their pricing personality, and lets your team save private strategy tags.",
        "table_title": "Institutional Memory for Your Desk",
        "rows": [
            ("Historical Move Timeline", "Tracks every neighbor shift", "Disappears next morning"),
            ("Pricing Personality Tags", "Flags dumpers vs. yielders", "Guesswork from memory"),
            ("Private Hotel Strategy Notes", "Isolated to your account", "Scattered across emails"),
        ],
        "cta": "Watch 10-Sec Walkthrough & Open Portal",
    },
    {
        "step": 16, "day": 31, "target_role": "GM / Owner", "dept_filter": ("gm_executive", "general_info"),
        "subject": "99 48-hr hotel ai audit",
        "trigger": "Low-Friction Paid Wedge",
        "hook": "Want a complete 48-hour operational review of {hotel_name}'s OTA parity leaks, direct booking engine, and front-desk automation opportunities — without a $10,000 consultant retainer?",
        "basic": "In addition to our $0 Free Starter and $99/mo automated daily online rate-comparison platform, we offer a one-time $99 48-Hour Hospitality AI Audit tailored specifically to your {area} property.",
        "table_title": "What's Included in the $99 48-Hr Audit",
        "rows": [
            ("Full OTA & Suite Parity Map", "Live {area} checkout math", "Generic slide decks"),
            ("Front Desk & Voice Ops Blueprint", "EN/ES direct-booking capture", "$5k–$10k agency fees"),
            ("Turnaround Time", "48 hours from Miami team", "4–6 weeks consulting"),
        ],
        "cta": "Watch 10-Sec Overview & Book or Explore",
    },
    {
        "step": 17, "day": 33, "target_role": "Front Desk / MOD", "dept_filter": ("front_office_mod", "general_info"),
        "subject": "bilingual desk concierge",
        "trigger": "Direct Interactive Proof",
        "hook": "How many late-night walk-in or Spanish-speaking callers hang up and book on Booking.com (at 18% commission) when the front desk is busy checking in a line of guests?",
        "basic": "Alongside our automatic 6:00 AM competitor rate comparison platform, you can test our live English/Spanish Hospitality Voice Concierge right on hotelrateintel.com to hear how AI answers rate & property questions naturally.",
        "table_title": "Capture Direct Inquiries 24/7",
        "rows": [
            ("Bilingual Voice & Chat", "English & Spanish live demo", "Voicemail or hold music"),
            ("Rate-Parity Awareness", "Knows your live Direct BAR", "Disconnected call centers"),
            ("Direct Booking Savings", "Keeps 18% OTA commission", "Lost to third-party OTAs"),
        ],
        "cta": "Watch 10-Sec Walkthrough & Test Voice Demo",
    },
    {
        "step": 18, "day": 35, "target_role": "GM / Multi-Property Owner", "dept_filter": ("gm_executive", "sales_groups"),
        "subject": "multi-property miami rates",
        "trigger": "Bundle Value",
        "hook": "Managing 2 to 5 properties across South Beach, Mid-Beach, North Beach, or Wynwood shouldn't require paying $500 per building for separate rate-shopping logins.",
        "basic": "HotelRateIntel automatically scans OTAs and local competitor websites across every Miami corridor every morning — and our $399/mo Multi-Property Group plan covers up to 5 hotels with isolated property logins and one unified group view.",
        "table_title": "Multi-Property Economics (Up to 5 Hotels)",
        "rows": [
            ("5 Properties Combined", "$399/mo total ($80/hotel)", "$2,000–$2,500+/mo enterprise"),
            ("Isolated Property Logins", "Included per GM / Desk", "Per-seat upcharges"),
            ("In-Person Miami Review", "Monthly local strategy sync", "Remote support only"),
        ],
        "cta": "Watch the 10-Second Walkthrough",
    },
    {
        "step": 19, "day": 37, "target_role": "GM & Reservations", "dept_filter": ("gm_executive", "reservations"),
        "subject": "10-second hotel walkthrough",
        "trigger": "Visual Simplicity",
        "hook": "If you only have 10 seconds between check-ins, hit play below to see how independent Miami hotels replace 20 morning browser tabs with one calm 6:00 AM rate comparison screen.",
        "basic": "HotelRateIntel automatically compares Booking.com, Expedia, Agoda, Vio.com, Trip.com, and your neighboring {area} hotels every morning — with exact Suite-vs-Suite matching, live OOO/OOS holds, and month-to-month pricing starting at $0 Free.",
        "table_title": "3 Things You'll See in 10 Seconds",
        "rows": [
            ("1. Multi-OTA Parity Ladder", "Spot undercuts instantly", "Hidden in 15 tabs"),
            ("2. Suite-vs-Suite Checkout", "Resort fees + 14% tax", "Misleading entry averages"),
            ("3. Live OOO / OOS Room Ops", "Instant net-occ BAR target", "Manual guesswork"),
        ],
        "cta": "Play 10-Second Walkthrough Now",
    },
    {
        "step": 20, "day": 39, "target_role": "All Unreplied", "dept_filter": ("gm_executive", "reservations", "front_office_mod", "general_info"),
        "subject": "keeping your free portal",
        "trigger": "Polite Breakup / Zero Pressure",
        "hook": "I won't keep filling your inbox — just wanted to let you know we're keeping {hotel_name}'s free {area} rate-comparison link open whenever your team wants a second set of eyes on OTA parity.",
        "basic": "Whenever you want automatic 6:00 AM online rate comparisons across Booking.com, Expedia, Agoda, Vio.com, and local {area} hotels — with Suite-vs-Suite math and $0 Free Starter access — you can open it anytime with no obligation.",
        "table_title": "Always Here Locally in Miami",
        "rows": [
            ("Free Starter Tier", "$0/mo (3 local comps)", "No credit card required"),
            ("Boutique Core", "$99/mo month-to-month", "No annual lock-in"),
            ("Direct Local Line", "Text/Call (786) 970-8366", "Real Miami hotelier"),
        ],
        "cta": "Watch 10-Sec Overview & Keep Your Link",
    },
]


def _get_resend_key(cfg):
    rkey = (cfg.get("outreach", {}).get("resend_api_key") or os.environ.get("RESEND_API_KEY") or "").strip()
    if not rkey:
        env_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local")
        if os.path.exists(env_p):
            with open(env_p, encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("RESEND_API_KEY="):
                        rkey = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    return rkey


def make_unsub_url(email: str) -> str:
    em = (email or "").strip().lower()
    secret = (os.environ.get("HRI_UNSUB_SECRET") or os.environ.get("HRI_AUTH_KEY") or "hri-miami-2026").encode("utf-8")
    sig = hmac.new(secret, em.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"https://hotelrateintel.com/api/public/unsubscribe?email={urllib.parse.quote(em)}&sig={sig}"


def is_noise_email(email: str) -> bool:
    low = (email or "").strip().lower()
    return any(pat in low for pat in NON_MIAMI_NOISE_PATTERNS)


def record_suppression(conn, email: str, reason: str, detail: str = ""):
    em = (email or "").strip().lower()
    if not em or "@" not in em:
        return
    dom = em.split("@", 1)[1]
    now = time.time()
    row = conn.execute("SELECT soft_bounce_count FROM email_suppressions WHERE email=?", (em,)).fetchone()
    if reason == "soft_bounce":
        cnt = (int(row["soft_bounce_count"]) if row else 0) + 1
        final_reason = "repeated_soft_bounce" if cnt >= 2 else "soft_bounce_warning"
        conn.execute(
            """INSERT INTO email_suppressions(email, domain, reason, soft_bounce_count, suppress_domain, detail, updated_at)
               VALUES(?,?,?,?,0,?,?)
               ON CONFLICT(email) DO UPDATE SET reason=excluded.reason, soft_bounce_count=excluded.soft_bounce_count, detail=excluded.detail, updated_at=excluded.updated_at""",
            (em, dom, final_reason, cnt, detail, now),
        )
    else:
        suppress_dom = 1 if reason in ("spam_complaint_block", "complaint", "blocked") else 0
        conn.execute(
            """INSERT INTO email_suppressions(email, domain, reason, soft_bounce_count, suppress_domain, detail, updated_at)
               VALUES(?,?,?,0,?,?,?)
               ON CONFLICT(email) DO UPDATE SET reason=excluded.reason, suppress_domain=MAX(suppress_domain, excluded.suppress_domain), detail=excluded.detail, updated_at=excluded.updated_at""",
            (em, dom, reason, suppress_dom, detail, now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO do_not_contact(value, channel, reason, added_at) VALUES(?,?,?,?)",
            (em, "email", reason, now),
        )
    conn.commit()


def is_suppressed(conn, email: str) -> tuple[bool, str]:
    em = (email or "").strip().lower()
    if not em or "@" not in em:
        return True, "invalid_email"
    if is_noise_email(em):
        return True, "non_miami_or_noise_role"
    dom = em.split("@", 1)[1]
    if conn.execute("SELECT 1 FROM do_not_contact WHERE lower(value)=?", (em,)).fetchone():
        return True, "do_not_contact"
    r = conn.execute("SELECT reason, soft_bounce_count FROM email_suppressions WHERE email=?", (em,)).fetchone()
    if r:
        if r["reason"] != "soft_bounce_warning" or int(r["soft_bounce_count"] or 0) >= 2:
            return True, r["reason"]
    d = conn.execute("SELECT reason FROM email_suppressions WHERE domain=? AND suppress_domain=1", (dom,)).fetchone()
    if d:
        return True, f"domain_blocked:{d['reason']}"
    return False, ""


def clean_non_miami_contacts(conn) -> dict:
    """Remove non-Miami sister hotel emails & Virginia Beach 757 phones from SQLite."""
    removed_emails = 0
    for r in conn.execute("SELECT id, value FROM contacts WHERE kind='email'").fetchall():
        if is_noise_email(r["value"]):
            conn.execute("DELETE FROM contacts WHERE id=?", (r["id"],))
            removed_emails += 1
    removed_phones = 0
    for r in conn.execute("SELECT id, value FROM contacts WHERE kind='phone'").fetchall():
        v = r["value"] or ""
        if "(757)" in v or "(206)" in v or "(310)" in v or "(212)" in v or v.startswith("+34"):
            conn.execute("DELETE FROM contacts WHERE id=?", (r["id"],))
            removed_phones += 1
    conn.commit()
    return {"removed_non_miami_emails": removed_emails, "removed_non_miami_phones": removed_phones}


def check_dns_deliverability(domain: str = "hotelrateintel.com") -> dict:
    def _q(name):
        try:
            out = subprocess.run(
                ["nslookup", "-type=txt", name, "8.8.8.8"],
                capture_output=True, text=True, timeout=6,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout
            return out
        except Exception:
            return ""
    dkim = "p=migfma0g" in _q(f"resend._domainkey.{domain}").lower()
    dmarc = "v=dmarc1" in _q(f"_dmarc.{domain}").lower()
    spf_root = "v=spf1" in _q(domain).lower()
    return {"domain": domain, "dkim_resend": dkim, "dmarc": dmarc, "spf_root": spf_root}


def render_step_email(step_num: int, hotel: dict, recipient_email: str) -> dict:
    tpl = next((s for s in CAMPAIGN_20_STEPS if s["step"] == step_num), CAMPAIGN_20_STEPS[0])
    hotel_name = hotel["name"]
    clean_base = hotel_name.split(",")[0].split("(")[0].split("/")[0].replace("Hotel ", "").strip()
    words = clean_base.split()
    short_name = " ".join(words[:3]) if len(words) > 3 else clean_base
    if not short_name:
        short_name = hotel_name
    area = hotel.get("area") or "Miami Beach"
    area_lower = area.lower().split("(")[0].strip()
    fmt = {
        "hotel_name": hotel_name,
        "short_name": short_name.lower(),
        "area": area,
        "area_lower": area_lower,
    }
    subject = tpl["subject"].format(**fmt)
    hook = tpl["hook"].format(**fmt)
    basic = tpl["basic"].format(**fmt)
    demo_url = f"https://hotelrateintel.com/portal?demo_hotel={hotel['id']}"
    unsub_url = make_unsub_url(recipient_email)

    tr_html = "".join(
        f"<tr>"
        f"<td style='padding:9px 11px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#0b1b3b;font-weight:700;'>{r[0].format(**fmt)}</td>"
        f"<td style='padding:9px 11px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#1d4ed8;font-weight:800;background:#eff6ff;'>{r[1].format(**fmt)}</td>"
        f"<td style='padding:9px 11px;border-bottom:1px solid #e2e8f0;font-size:13px;color:#475569;'>{r[2].format(**fmt)}</td>"
        f"</tr>"
        for r in tpl["rows"]
    )

    html = f"""<!doctype html>
<html>
<body style="margin:0;padding:20px;background:#f2f6fd;font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',Roboto,sans-serif;color:#0b1b3b;">
  <div style="max-width:630px;margin:0 auto;background:#ffffff;border:1px solid #dce7f8;border-radius:18px;overflow:hidden;">
    <div style="background:#0d255b;padding:13px 22px;color:#ffffff;">
      <div style="font-size:10.5px;letter-spacing:0.08em;text-transform:uppercase;font-weight:800;color:#93c5fd;">
        HOTELRATEINTEL MIAMI · MADE BY HOTELIERS (20 YRS LUXURY SERVICE)
      </div>
    </div>
    <div style="padding:24px;">
      <p style="font-size:15px;line-height:1.65;color:#0b1b3b;font-weight:700;margin:0 0 14px;">{hook}</p>
      <div style="background:#f5f9ff;border:1px solid #dce7f8;border-left:4px solid #2563eb;border-radius:10px;padding:13px 15px;font-size:13.5px;line-height:1.6;color:#1e293b;margin:0 0 18px;">
        {basic}
      </div>

      <div style="margin:0 0 18px;text-align:center;">
        <a href="{BLOGS_VIDEO_LINK}" style="display:block;text-decoration:none;border:1px solid #dce7f8;border-radius:14px;overflow:hidden;">
          <img src="{VIDEO_POSTER_URL}" alt="Watch 10-Second HotelRateIntel Miami Walkthrough" width="580" style="display:block;width:100%;max-width:580px;height:auto;border:0;" />
        </a>
        <div style="font-size:11.5px;color:#475b80;margin-top:6px;">
          <a href="{BLOGS_VIDEO_LINK}" style="color:#1d4ed8;font-weight:700;text-decoration:none;">▶ Watch 10-Second Walkthrough &amp; Read Miami Hotelier Guides on hotelrateintel.com/#blogs &rarr;</a>
        </div>
      </div>

      <div style="font-size:13px;font-weight:800;color:#0b1b3b;margin:0 0 8px;">{tpl['table_title'].format(**fmt)}</div>
      <table style="width:100%;border-collapse:collapse;border:1px solid #dce7f8;border-radius:10px;overflow:hidden;margin:0 0 18px;">
        <thead>
          <tr style="background:#f5f9ff;text-align:left;">
            <th style="padding:8px 11px;font-size:11px;text-transform:uppercase;color:#475b80;border-bottom:1px solid #dce7f8;">Hospitality Need</th>
            <th style="padding:8px 11px;font-size:11px;text-transform:uppercase;color:#1d4ed8;border-bottom:1px solid #dce7f8;background:#eff6ff;">HotelRateIntel (Miami)</th>
            <th style="padding:8px 11px;font-size:11px;text-transform:uppercase;color:#475b80;border-bottom:1px solid #dce7f8;">Others / Manual</th>
          </tr>
        </thead>
        <tbody>{tr_html}</tbody>
      </table>

      <div style="margin:18px 0;">
        <a href="{BLOGS_VIDEO_LINK}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;padding:11px 18px;border-radius:10px;font-size:13px;font-weight:800;margin-right:8px;">
          {tpl['cta']} &rarr;
        </a>
        <a href="{demo_url}" style="display:inline-block;background:#f2f6fd;color:#0b1b3b;border:1px solid #dce7f8;text-decoration:none;padding:10px 16px;border-radius:10px;font-size:12.5px;font-weight:700;">
          Open {short_name.title()} Live Demo
        </a>
      </div>

      <p style="font-size:13px;line-height:1.6;color:#334155;margin:0 0 16px;">
        Starts at <strong>$0/mo Free Starter</strong> (3 local comps) or <strong>$99/mo Core</strong> month-to-month. Want me to text or email your 1-page {area} parity sheet?
      </p>

      <div style="font-size:12px;color:#64748b;border-top:1px solid #e2e8f0;padding-top:13px;line-height:1.55;">
        <strong style="color:#0b1b3b;">Jasmel Acosta</strong> · Founder, HotelRateIntel · North Miami, FL 33161<br/>
        Call / Text / WhatsApp: <a href="tel:+17869708366" style="color:#1d4ed8;text-decoration:none;font-weight:700;">+1 (786) 970-8366</a> · <a href="{BLOGS_VIDEO_LINK}" style="color:#1d4ed8;text-decoration:none;">hotelrateintel.com/#blogs</a><br/>
        <span style="font-size:11px;">Prefer not to hear from us? <a href="{unsub_url}" style="color:#64748b;text-decoration:underline;">1-Click Unsubscribe</a> or reply STOP.</span>
      </div>
    </div>
  </div>
</body>
</html>"""

    text = (
        f"{hook}\n\n{basic}\n\n"
        f"Watch our 10-second minimalist walkthrough & Miami hotelier guides: {BLOGS_VIDEO_LINK}\n"
        f"Inspect {hotel_name}'s live zero-login demo: {demo_url}\n\n"
        f"Starts at $0/mo Free Starter or $99/mo Core month-to-month. Worth a quick look?\n\n"
        f"— Jasmel Acosta | HotelRateIntel (North Miami, FL 33161) | +1 (786) 970-8366\n"
        f"Unsubscribe instantly: {unsub_url}"
    )

    return {
        "step": step_num,
        "subject": subject,
        "html": html,
        "text": text,
        "headers": {
            "List-Unsubscribe": f"<{unsub_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
        "unsub_url": unsub_url,
    }


def select_batch_recipients(conn, step_num: int, limit: int = 15) -> list[dict]:
    """Select verified, non-suppressed Miami hotel recipients honoring 48h cadence spacing."""
    tpl = next((s for s in CAMPAIGN_20_STEPS if s["step"] == step_num), CAMPAIGN_20_STEPS[0])
    depts = tpl["dept_filter"]
    now = time.time()
    hotels = [dict(r) for r in conn.execute("SELECT * FROM hotels ORDER BY id ASC")]
    picked = []
    seen_emails = set()

    for h in hotels:
        cts = conn.execute(
            "SELECT value, department FROM contacts WHERE hotel_id=? AND kind='email' ORDER BY id ASC",
            (h["id"],),
        ).fetchall()
        # Prioritize matching department for this step, else fallback to best clean hotel email
        ordered = sorted(cts, key=lambda c: (0 if (c["department"] or "general_info") in depts else 1))
        chosen = None
        for c in ordered:
            em = (c["value"] or "").strip().lower()
            if em in seen_emails:
                continue
            sup, _ = is_suppressed(conn, em)
            if sup:
                continue
            # Check if this step was already sent to this email
            if conn.execute("SELECT 1 FROM campaign_sends WHERE email=? AND step_number=?", (em, step_num)).fetchone():
                continue
            # Check 46h minimum spacing from any prior step
            last = conn.execute("SELECT MAX(sent_at) m FROM campaign_sends WHERE email=?", (em,)).fetchone()
            if last and last["m"] and (now - float(last["m"])) < MIN_SPACING_SEC:
                continue
            chosen = (em, c["department"] or "general_info")
            break
        if chosen:
            seen_emails.add(chosen[0])
            picked.append({"hotel": h, "email": chosen[0], "department": chosen[1]})
        if len(picked) >= limit:
            break
    return picked


def send_via_resend(rkey: str, to_email: str, rendered: dict) -> tuple[bool, str, str]:
    payload = {
        "from": FROM_EMAIL,
        "to": [to_email],
        "reply_to": [REPLY_TO],
        "subject": rendered["subject"],
        "text": rendered["text"],
        "html": rendered["html"],
        "headers": rendered["headers"],
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {rkey}",
            "Content-Type": "application/json",
            "User-Agent": "HotelRateIntel/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode("utf-8"))
            return True, str(d.get("id") or ""), ""
    except urllib.error.HTTPError as e:
        return False, "", f"HTTP {e.code}: {e.read().decode('utf-8')[:220]}"
    except Exception as e:
        return False, "", str(e)


def main():
    parser = argparse.ArgumentParser(description="HotelRateIntel 20-Email Campaign & Deliverability Engine")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Inspect DNS deliverability, clean recipient pool, and suppression counts")
    sub.add_parser("clean-contacts", help="Remove non-Miami sister hotel emails and out-of-market phones")

    p_sup = sub.add_parser("suppress", help="Suppress an email or domain (bounce/complaint/unsubscribe/replied)")
    p_sup.add_argument("email")
    p_sup.add_argument("--reason", default="manual_opt_out", choices=["hard_bounce", "soft_bounce", "spam_complaint_block", "unsubscribed", "replied", "manual_opt_out"])
    p_sup.add_argument("--detail", default="")

    p_send = sub.add_parser("send", help="Send test, dry-run, or live campaign batch")
    p_send.add_argument("--step", type=int, default=1)
    p_send.add_argument("--limit", type=int, default=15)
    p_send.add_argument("--test-to", default="")
    p_send.add_argument("--dry-run", action="store_true")
    p_send.add_argument("--live", action="store_true")

    args = parser.parse_args()
    cfg = cfgmod.load()
    conn = dbmod.open_db(cfg["database"])
    try:
        if args.cmd == "clean-contacts":
            res = clean_non_miami_contacts(conn)
            print(json.dumps({"ok": True, **res}, indent=2))
            return

        if args.cmd == "suppress":
            record_suppression(conn, args.email, args.reason, args.detail)
            print(f"Suppressed {args.email} (reason={args.reason})")
            return

        if args.cmd == "status":
            dns = check_dns_deliverability()
            sup_rows = conn.execute("SELECT reason, COUNT(*) c FROM email_suppressions GROUP BY reason").fetchall()
            sent_cnt = conn.execute("SELECT COUNT(*) c FROM campaign_sends").fetchone()["c"]
            ready_step1 = select_batch_recipients(conn, step_num=1, limit=100)
            print(json.dumps({
                "dns": dns,
                "resend_key_configured": bool(_get_resend_key(cfg)),
                "steps_loaded": len(CAMPAIGN_20_STEPS),
                "ready_miami_hotels_step1": len(ready_step1),
                "campaign_sends_total": sent_cnt,
                "suppressions_by_reason": {r["reason"]: r["c"] for r in sup_rows},
            }, indent=2))
            return

        if args.cmd == "send":
            rkey = _get_resend_key(cfg)
            if args.test_to:
                h = dict(conn.execute("SELECT * FROM hotels WHERE id=23").fetchone() or conn.execute("SELECT * FROM hotels LIMIT 1").fetchone())
                rendered = render_step_email(args.step, h, args.test_to)
                ok, rid, err = send_via_resend(rkey, args.test_to, rendered)
                print(json.dumps({"ok": ok, "to": args.test_to, "step": args.step, "subject": rendered["subject"], "resend_id": rid, "error": err}, indent=2))
                return

            limit = min(int(args.limit), 80)  # Hard safety cap below Resend 100/day free ceiling
            batch = select_batch_recipients(conn, step_num=args.step, limit=limit)
            if args.dry_run or not args.live:
                print(f"DRY-RUN Step #{args.step} ({len(batch)} clean Miami hotels ready):")
                for idx, b in enumerate(batch, start=1):
                    rendered = render_step_email(args.step, b["hotel"], b["email"])
                    print(f"  {idx:2d}. {b['hotel']['name'][:34]:34s} -> {b['email']:42s} | subj: {rendered['subject']}")
                return

            if not rkey:
                print("ERROR: RESEND_API_KEY missing")
                sys.exit(1)
            sent_ok = 0
            for idx, b in enumerate(batch, start=1):
                em = b["email"]
                if not verify_email_mx(em):
                    record_suppression(conn, em, "hard_bounce", "Failed live MX check pre-send")
                    print(f"  [SKIP-MX] {em} suppressed")
                    continue
                rendered = render_step_email(args.step, b["hotel"], em)
                ok, rid, err = send_via_resend(rkey, em, rendered)
                status = "sent_live" if ok else "failed"
                conn.execute(
                    "INSERT OR REPLACE INTO campaign_sends(hotel_id, email, department, step_number, subject, resend_id, status, delivery_status, sent_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (b["hotel"]["id"], em, b["department"], args.step, rendered["subject"], rid, status, "sent" if ok else "failed", time.time()),
                )
                conn.commit()
                if ok:
                    sent_ok += 1
                    print(f"  [{idx}/{len(batch)}] SENT -> {em} | resend_id={rid}")
                else:
                    print(f"  [{idx}/{len(batch)}] ERR  -> {em} | {err}")
                time.sleep(1.2)
            print(f"Batch complete: {sent_ok}/{len(batch)} sent cleanly.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
