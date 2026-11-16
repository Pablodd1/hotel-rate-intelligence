# Hotel Rate Intelligence (HRI) — Miami Go-To-Market, Outbound & Launch Playbook

**Owner / Operator:** Jasmel Acosta (North Miami / Miami Beach, FL)  
**Core Offer:** `$99/mo` Flat Morning Rate Brief + OTA Parity Tracker (7-Day Free Trial, Zero Contract, No Per-Room Fees)  
**Benchmark Wedge:** Enterprise rate-shopping suites (`Lighthouse`, `RateGain`, `OTA Insight` addons) typically price small hotels out at `$400–$700+/mo` with annual commitments. At **`$99/mo` (`$3.30/day`)**, HRI costs **less than one-third of a single Miami room night** (`$307/nt` live market average).

---

## 1. Live Verified Miami Market Snapshot (Baseline Data from Local SQLite Scan)

Every figure below comes strictly from our live Xotelo + website MX + public-record verification run (`run.py hunt-leads` & `run.py market-research`):

| Verified Metric | Live Result |
| :--- | :--- |
| **Total Verified Miami Properties** | **49** (`45` Hot · `3` Warm) |
| **Properties with Live Multi-OTA Quotes** | **44 / 49** (`$307/nt` market average) |
| **Active Live OTA Parity Undercuts** | **31 / 44 (`70.5%`)** |
| **Largest Verified Undercut Example** | **Beacon South Beach Hotel**: `$123` retail vs `$68` on `Agoda.com` (`-44.7%`) |
| **Verified Cited Decision-Makers (GM/Owner)** | **25** properties with cited public-record contacts |
| **DNS MX-Verified Email Properties** | **39** properties (18 dead/no-MX addresses & 2 closed hotels purged) |
| **Verified Front Desk / Corporate Phones** | **47** properties |

### Corridor Breakdown (Live Today)

| Miami Corridor | Hotels Tracked | Live Quotes | Avg Live BAR | Live OTA Undercuts |
| :--- | :---: | :---: | :---: | :---: |
| **Mid-Beach** | 7 | 7 | `$637/nt` | 2 |
| **Wynwood / Downtown / Coral Gables** | 5 | 5 | `$298/nt` | 5 |
| **South Beach** | 24 | 23 | `$279/nt` | 18 |
| **North Beach / Bay Harbor / Sunny Isles** | 10 | 6 | `$130/nt` | 4 |
| **MiMo / Biscayne Blvd (North Miami)** | 3 | 3 | `$121/nt` | 2 |

> **Highest-Leverage Cluster Targets:** Independent owner-operators (`Vagabond Group` — Avra Jain & Dalia Lagoa; `Savoy Miami Independent`; `The Betsy` — Jonathan Plutzik & Jeff Lehman) plus multi-property Miami groups visible directly in the database (`Yurbban Hospitality Group` — 2 properties: `Uma House` + `Lennox`; `South Beach Group / Think` — `Seaside All Suites` + `Waterside Hotel & Suites`, plus `The Plymouth`). Closing one multi-property operator converts 2–5 properties at `$199–$399/mo`.

---

## 2. Flexible Pricing Experiments & Unit Economics (`$99/mo` Core Anchor)

All pricing experiments can be switched live in **Tab `2. Leads & Outbound`** (`Pricing Experiment` bar) or via `?price=N`, dynamically updating ROI multiples and personalized Email / SMS / WhatsApp / Voice scripts across all 49 hotels:

| Experiment Plan | Monthly Price | Target Segment & Hypothesis | 30 Hotels MRR | 100 Hotels MRR |
| :--- | :---: | :--- | :---: | :---: |
| **`intro_49`** | **`$49/mo` Month 1 -> `$99/mo`** | Fast frictionless close during local walk-ins & cold calls for the first 10 Miami properties | `$1,470` M1 (`$2,970` M2+) | `$9,900` settled |
| **`pilot_79`** | **`$79/mo` Lifetime Cohort** | "Founding 10" incentive if a GM insists on an early-adopter lock | `$2,370/mo` | `$7,900/mo` |
| **`founder_99` (Anchor)** | **`$99/mo` Flat (`$3.30/day`)** | **Primary positioning:** Independent 15–80 room hotels; zero annual contract, 6 AM email & Telegram brief | **`$2,970/mo`** | **`$9,900/mo`** |
| **`growth_149`** | **`$149/mo`** | High-ADR boutiques (`$250+/nt`) needing morning + afternoon scans & full OTA parity tracking | `$4,470/mo` | `$14,900/mo` |
| **`pro_199` (Upsell)** | **`$199/mo`** | Adds instant SMS/WhatsApp undercut alerts + Overnight Courtesy Call-Around Desk | `$5,970/mo` | `$19,900/mo` |
| **`portfolio_399`** | **`$399/mo`** | Multi-property owners / small Miami groups (up to 5 properties + monthly local review) | `$11,970/mo` | — |

**Target Payback Math:** With **1.5–4% net variable cost per subscriber** (once automated via Brevo + Twilio + Gemini Flash-Lite), **12 hotels at `$99/mo` (`$1,188/mo`)** makes the business solidly profitable even with full multi-channel SMS, Voice AI, and domain infrastructure active.

---

## 3. Four-Channel Outbound Sequence (Signal-Based — Live Proof Only)

Every outreach message embeds a **live property proof line** (e.g., exact live Xotelo BAR vs lowest OTA rate or corridor comp average) + the **7-morning free 6 AM brief** + opt-out footer:

1. **Day 1 AM (Email — Brevo/Resend Free Tier + Printable 1-Page PDF/HTML Audit):**
   - Lead with their real live parity gap or corridor comparison + `/audit?hotel_id=N` summary + `$99/mo` flat framing.
   - *Rule:* Only send to DNS MX-verified domains (`39` verified in DB; dead MX purged automatically).
2. **Day 1 PM (Local Walk-In — North Miami / MiMo -> North Beach -> South Beach Routes):**
   - Print 8 copies of `/audit?hotel_id=N` from the dashboard before walking into MiMo / North Beach / Ocean Dr lobbies Tue–Thu `10:15–11:45 AM` or `2:00–3:30 PM`. Hand the 1-page live sheet to the Front Desk / GM; offer `$49` Month 1 / `$99/mo` ongoing.
3. **Day 2 (SMS or WhatsApp Business via Twilio or 1-Click Native `sms:` / `wa.me`):**
   - Short (<300 chars) proof ping referencing live neighbor rates + `"Reply YES for your 7-day free brief or STOP to opt out."`
4. **Day 3 (Voice Call — Vapi.ai / Bland.ai / Direct `tel:` Desk Call-Around):**
   - Open with gatekeeper bypass asking for the named GM/Owner -> 25-second live proof opener -> 7-morning free trial close (zero credit card upfront).
5. **Day 5 (Follow-Up Email & Social Inbound Loop):**
   - Share corridor compression warning (Hard Rock Stadium weekends, Art Basel Dec 3–6, Boat Show Feb 11–15) + live rate delta.

---

## 4. Social Launch Assets & Buffer Staging

- **5 data-backed launch posts** (`LinkedIn Founder Launch`, `LinkedIn Parity Study`, `Instagram / Reels`, `X Thread`, `Founding Cohort Offer`) are live inside `dashboard/index.html` Tab `2. Leads & Outbound` and via `python run.py market-research`.
- **3 Ideas Staged in Buffer (`My Organization` / `jasmelacosta@gmail.com`):** Saved safely as **Ideas** (`#1 LinkedIn Anchor`, `#2 LinkedIn Parity Study`, `#3 Instagram Launch`) — zero posts were scheduled onto any unrelated connected channels (`CEDEXX`). When you connect your dedicated HRI LinkedIn/Instagram pages inside Buffer, convert those Ideas directly into scheduled posts.

---

## 5. Exact Setup, Budget & Compliance Checklist to Go 100% Live

Currently `outreach.mode = "dry_run"` in `config.json` (all 4 channels safely log drafts + generate 1-click `mailto:`, `sms:`, `wa.me`, and `tel:` links without faking deliveries).

### Itemized Starter Budget (`~$38–$89/mo` Total Variable Stack)

| Channel / Tool | Provider & Cost | Free / DIY Alternative | Setup Key Field (`6. Setup` Tab or Env) |
| :--- | :--- | :--- | :--- |
| **Dedicated Cold Outreach Domain + Inbox** | Google Workspace / Zoho + Cloudflare (`~$12–$15/mo` + `$12/yr` domain) | Send 1-by-1 via `mailto:` from Gmail today (`$0`) | Domain SPF/DKIM/DMARC before bulk cold email |
| **Email Dispatch API** | **Brevo** (`300 emails/day FREE`, `$0/mo`) or **Resend** (`3,000/mo FREE`) | Built-in SMTP (`smtp-relay.brevo.com:587`) | `brevo_api_key` OR `smtp_user` + `smtp_pass` |
| **SMS + WhatsApp Business** | **Twilio** (`$1.15/mo` 305/786 local number + `~$0.0083/SMS` + `$15–$25` A2P 10DLC reg) | 1-click native `sms:` / `https://wa.me/` links (`$0`) | `twilio_account_sid`, `twilio_auth_token`, `twilio_from_phone`, `twilio_whatsapp_from` |
| **AI Voice Calls & Recording** | **Vapi.ai** or **Bland.ai** (`~$0.07–$0.12/min`, `~$15–$30/mo` starter credit) | Direct `tel:` + browser mic recorder in Tab 3 (`$0`) | `vapi_api_key` + `vapi_phone_number_id` (or `bland_api_key`) |
| **Morning Brief Delivery (Owner)** | **Telegram Bot** (`$0/mo`) | Printed Console / Email | `telegram.bot_token`, `telegram.chat_id` |
| **AI Pitch Polish (Optional)** | **Gemini 2.5 Flash-Lite** (`~$0–$1/mo`) | Local deterministic brief engine (`$0`) | `GEMINI_API_KEY` env var |
| **Stripe Billing (`$49`/`$99`/`$199`/`$399`)** | `2.9% + $0.30` per transaction (`$0/mo` fixed) | Payment Links | Create Stripe Payment Links per tier |

### U.S. & Florida Outbound Compliance Rules
- **CAN-SPAM (Email):** Include your valid physical mailing address (`North Miami, FL 33161` default in `config.json`), non-deceptive subject lines, and honor `"STOP"`/`opt-out` requests immediately (`POST /api/opt-out` -> `do_not_contact` table enforces this automatically).
- **A2P 10DLC & TCPA / Florida Telephone Solicitation Act (SMS & Auto-Dialed Voice):** Register your brand + campaign on Twilio A2P 10DLC before sending automated B2B SMS; call strictly between **8:00 AM – 8:00 PM local time** for sales pitches (quiet `23:30–04:00` night-audit courtesy exchanges remain human/opt-in peer front-desk exchanges); honor every `STOP` / Do-Not-Call request permanently.

---

## 6. 30-Day Execution Calendar (Target: First 10–30 Paid Miami Properties)

- **Week 1 (MiMo, North Miami & North Beach Blitz):** Configure Brevo (`$0`) + warm secondary sending domain; print 15 audit sheets via `/audit?hotel_id=N`; walk Route 1 (`MiMo/79th St`: New Yorker, Vagabond, Biscayne) and Route 2 (`North Beach`: Waterside, Seaside, Altair, Oceanside) Tue–Thu; send Day 1 MX-verified emails to all `39` reachable properties; activate `7-day free trial` + `$49` Month 1 founding offer. **Goal: 5 free 6 AM brief trials active.**
- **Week 2 (South Beach Art Deco Walk + Voice Follow-Ups):** Walk Route 4 (park at 12th St Garage -> `Avalon`, `Colony`, `Pelican`, `Marlin`, `Victor`, `Greystone`, `Uma House`, `Cardozo`); call non-openers via Tab 3 / Voice; test `$99/mo` vs `$79/mo` cohort conversion. **Goal: 12 trials -> 4 paid customers (`$296–$396` MRR).**
- **Week 3 (Multi-Property Owners & Parity Upsells):** Pitch `Yurbban` (`Uma House` + `Lennox`), `SBG / Think` (`Seaside` + `Waterside` + `Plymouth`), and high-ADR Mid-Beach boutiques (`Faena`, `Palms`, `Circa 39`, `Palihouse`) on the `$199` / `$399` Portfolio tier using live Agoda/Vio undercut evidence. **Goal: 10–15 paid hotels (`$1,000–$1,800` MRR).**
- **Week 4 (Lock In Retention & Referral Loop):** Automate daily 6:00 AM Email + Telegram deliveries (`run.py send-briefs`), turn on Art Basel (`Dec 3–6`) compression alerts, and offer existing Miami clients 1 free month per neighbor GM referral. **Target 30-Day Milestone: 20–30 paid properties (`$1,980–$2,970+` MRR).**
