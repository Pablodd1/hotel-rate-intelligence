# Open-Source GitHub Landscape & Architecture Benchmark for Hotel Rate Intelligence (HRI)

This document maps the open-source GitHub ecosystem around **hotel rate shopping, OTA parity monitoring, metasearch scraping, and B2B hospitality lead intelligence**, and documents how **Hotel Rate Intelligence (`Pablodd1/hotel-rate-intelligence`)** consolidates and upgrades them into a self-hosted, zero-per-scrape-cost commercial platform.

---

## 1. Studied Open-Source Repositories & Technical Delta

| Repository / Project | Core Pattern Studied | Upstream Limitation | How HRI (`hotel-rate-intelligence`) Upgrades It |
|---|---|---|---|
| **`omkarcloud/booking-scraper`** | 4-endpoint API surface (`search`, `details`, `reviews`, `autocomplete`) + clean JSON normalization | Focused only on Booking.com; no direct-site rate comparison or B2B contact extraction | Combines OTA rates with direct hotel website BAR + decision-maker contact capture in one SQLite pipeline |
| **`flatrow-data-studio/booking-scraper-python`** | Historical price-tracker diff pattern (`prev_price → current_price` delta %) | Requires manual setup per run; no prospect scoring or alerting | Automated dual-horizon baseline (`14d` vs `30d` check-in) + instant `▲`/`▼` % movers in CLI, Telegram & Web UI |
| **`PRO100CHOK/booking-com-hotels-prices-reviews-scraper-python`** | Competitive-set property audit (room types, price bands, review counts) | Relies on paid Apify actors / proxies for every run | Self-hosted `curl_cffi` Chrome TLS impersonation + free Xotelo/TripAdvisor metasearch feed + Playwright stealth fallback |
| **`ScrapingBee/google-hotels-api` & `jongan69/hotels`** | Multi-OTA rate ladder (`Booking.com`, `Agoda`, `Expedia`, `Hotels.com`, `Official Site`) | Stops at raw price scraping; no parity violation math or sales playbook | Computes real-time **OTA Parity Status** (`UNDERCUT`, `PARITY`, `DIRECT_WIN`), % undercut, and annual RevPAR/commission leakage |
| **`gosom/google-maps-scraper`** | High-breadth local B2B lead discovery (phones, emails, websites, ratings, coordinates) | Generic business scraper with no hotel rate or parity context | `scripts/import_leads.py` + `hri/hotel_sites.py` normalize phones/emails/addresses and link them to live rate & parity hooks |
| **`aws-samples/sample-ai-hotel-revenue-management-system`** | Multi-agent revenue management & dynamic pricing recommendations | Heavy cloud lock-in (AWS Bedrock/Lambda) | 100% local-first / Vercel-portable stdlib Python server + deterministic ROI & outbound sales script generator (`hri/sales_engine.py`) |

---

## 2. Core Technical Upgrades Implemented in HRI v2

### A. Triple-Layer Rate & Parity Engine ([`hri/rate_engine.py`](file:///C:/Users/jasme/hotel-rate-intelligence/hri/rate_engine.py))
1. **Xotelo / TripAdvisor Live Metasearch API (`https://data.xotelo.com/api/rates` & `/api/list`)**:
   - Pulls live multi-OTA rates (`Booking.com`, `Agoda.com`, `Expedia.com`, `Hotels.com`, `Vio.com`, `Trip.com`) and seasonal price bands (`price_min`, `price_max`, `review_rating`, `review_count`) with zero WAF blocks and $0 API cost.
2. **Direct Website JSON-LD & Booking Engine Fingerprint**:
   - Uses `curl_cffi` (`impersonate="chrome"`) to inspect the hotel's official site for `schema.org/Offer` pricing and identifies the underlying CRS/booking engine (`SynXis / Sabre`, `Cloudbeds`, `Mews`, `TravelClick / iHotelier`, `Opera / IHG`).
3. **Playwright Stealth Booking.com Engine ([`hri/scraper.py`](file:///C:/Users/jasme/hotel-rate-intelligence/hri/scraper.py))**:
   - Optional residential-IP browser automation fallback when deep room-level DOM inspection is required.

### B. Contact Normalization & Decision-Maker Enrichment ([`hri/hotel_sites.py`](file:///C:/Users/jasme/hotel-rate-intelligence/hri/hotel_sites.py) & [`hri/db.py`](file:///C:/Users/jasme/hotel-rate-intelligence/hri/db.py))
- Automatically strips `mailto:` / `tel:` prefixes, normalizes US phone numbers to `(XXX) XXX-XXXX`, filters noisy regex street matches, and deduplicates across `homepage`, `/contact`, `/meetings`, and `/events` pages.
- Tracks 30 curated Miami Beach boutique & lifestyle hotels with **170+ verified business contacts**.

### C. Automated B2B Sales & Outbound Playbook Engine ([`hri/sales_engine.py`](file:///C:/Users/jasme/hotel-rate-intelligence/hri/sales_engine.py))
- Turns raw rate & parity observations into **ready-to-close sales assets** per property:
  - **Gatekeeper / Front-Desk Bypass Script**
  - **30-Second GM / Director of Revenue Opener** (citing the hotel's exact BAR, lowest OTA undercut, and 3 immediate neighbor rates)
  - **Objection-Handling Matrix** (word-for-word rebuttals for Cloudbeds/SynXis, manual checking, and budget objections)
  - **3-Step SMS / WhatsApp Sequence & LinkedIn DM**
  - **5-Step Cold & Marketing Email Sequence** with `mailto:` 1-click launch
  - **Property-Specific Annual RevPAR & Commission Recovery Calculator**
