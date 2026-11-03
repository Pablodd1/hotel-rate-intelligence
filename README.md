# Hotel Rate Intelligence (HRI) — Miami Beach Edition

Competitive **multi-OTA rate parity**, **direct-website contact capture**, **prospect scoring**, and an **automated B2B outbound sales engine** (call scripts, SMS/WhatsApp, 5-touch marketing emails, and RevPAR ROI calculator) for boutique-hotel markets. Built for **Miami Beach** — portable to any micro-market.

> **Upgrade of the open-source Booking.com / Google Hotels scraper & price-tracker ecosystem**:
> Self-hosted (zero paid Apify actors), combining **live multi-OTA rate ladders** (`Booking.com`, `Agoda`, `Expedia`, `Hotels.com`, `Direct BAR`), **OTA parity undercut alerts**, **normalized B2B contact capture** (170+ emails, direct phones, addresses, GM/Revenue roles across 30 Miami Beach hotels), **prospect scoring + annual RevPAR recovery math**, **daily Telegram/CLI briefs**, and a **5-tab Executive & Sales Command Center**.

---

## What It Does

1. **Multi-Channel Rate & Parity Engine (`hri/rate_engine.py`, `hri/scraper.py`)**:
   - **Live Multi-OTA Metasearch (`Xotelo / TripAdvisor`)**: Pulls live rates across Booking.com, Agoda, Expedia, Hotels.com, and Vio with zero WAF block and $0 per-scrape cost.
   - **Direct Website BAR & CRS Detection**: Inspects each hotel's official site via `curl_cffi` (`impersonate="chrome"`) for `schema.org/Offer` pricing and fingerprints the booking engine (`SynXis / Sabre`, `Cloudbeds`, `Mews`, `TravelClick`, `Opera`).
   - **OTA Parity Violation Detection**: Flags whether a property is in `PARITY`, `DIRECT_WIN`, or `UNDERCUT` (when a wholesaler/OTA undercuts the hotel's own website BAR—your strongest B2B sales hook).
2. **Normalized B2B Contact Capture (`hri/hotel_sites.py`, `hri/seed.py`)**:
   - Crawls hotel homepages + `/contact`, `/about`, `/meetings`, `/events` pages to extract and normalize emails, US phone numbers `(XXX) XXX-XXXX`, street addresses, and target decision-maker personas.
3. **Prospect Scoring & Annual ROI Calculator (`hri/prospects.py`)**:
   - Scores every property `0–100` (`hot / warm / watch`) with transparent buying signals and computes estimated **annual RevPAR + direct-booking commission recovery** (`+$45,000–$140,000+/yr`).
4. **Automated Outbound Sales & Marketing Playbook Engine (`hri/sales_engine.py`)**:
   - Dynamically generates per-hotel **Cold Call Scripts** (Front-Desk Gatekeeper Bypass, 30-Sec GM Opener with live neighbor rates, Discovery Questions, Objection Rebuttals, 7-Day Trial Close), **SMS/WhatsApp templates**, **LinkedIn DMs**, and a **5-Step Cold Email Sequence** with 1-click `mailto:` launch.
5. **5-Tab Interactive Command Center (`dashboard/index.html`, `hri/server.py`, `api/index.py`)**:
   - **Tab 1 — Executive Overview**: 6 KPI cards, Grouped BAR vs. Previous Scan Chart (Green ▲ / Coral ▼), Top Movers & Parity Undercuts, Hot Prospects, Collector Run Log.
   - **Tab 2 — Rate & OTA Parity Matrix**: Filterable multi-OTA rate ladder, seasonal min/max bands, parity status badges, and manual BAR ingest.
   - **Tab 3 — Scraped Hotel CRM & Contacts**: Searchable 30-hotel directory with 170+ verified contacts, deal stage pipeline (`new → contacted → audit_sent → pilot_active → closed_won`), and 1-click CSV export.
   - **Tab 4 — Prospect Scoring & ROI Pipeline**: Full 0–100 score cards with annual dollar upside.
   - **Tab 5 — Sales Playbook Hub**: Select any of the 30 hotels to get instant personalized Call Scripts, SMS, 5-Step Emails, and SaaS Pricing Tiers (`$299/mo`, `$599/mo`, `$1,499/mo`).

---

## Quick Start

```bash
git clone https://github.com/Pablodd1/hotel-rate-intelligence.git
cd hotel-rate-intelligence
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 run.py init-db
python3 run.py seed                # 30 real Miami Beach boutique hotels + 170+ verified contacts
python3 run.py collect --fast      # live multi-OTA rates + parity analysis + prospect scoring
python3 run.py collect             # full run including live hotel website HTML contact crawl
python3 run.py report              # print the daily executive & sales brief
python3 run.py pitch 4             # print full call script, SMS & email kit for hotel #4 (The Colony)
python3 run.py snapshot            # dump JSON snapshots to api/ for Vercel serverless deploy
python3 run.py dashboard           # http://127.0.0.1:8317
```

---

## Documentation & Playbooks

- **[`OPEN_SOURCE_GITHUB_RESEARCH.md`](OPEN_SOURCE_GITHUB_RESEARCH.md)** — Benchmark of open-source GitHub hotel scrapers (`omkarcloud/booking-scraper`, `flatrow-data-studio`, `PRO100CHOK`, `ScrapingBee/google-hotels-api`, `jongan69/hotels`, `gosom/google-maps-scraper`) and our technical delta.
- **[`SALES_AND_MARKETING_PLAYBOOK.md`](SALES_AND_MARKETING_PLAYBOOK.md)** — Complete B2B sales scripts, gatekeeper bypass, objection handling matrix, SMS/WhatsApp sequences, 5-step cold email templates, and pricing tiers (`$299 / $599 / $1,499`).

## License

MIT — see [LICENSE](LICENSE).
