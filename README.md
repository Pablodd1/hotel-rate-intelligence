# Hotel Rate Intelligence (HRI)

Competitive rate + contact intelligence for boutique-hotel markets. Built for
Miami Beach — portable to any micro-market.

> Upgrade of the open-source **Booking.com scraper / price-tracker** use case:
> same problem, but self-hosted (no paid Apify actor), with a **contact-capture
> layer** (who to sell rate intelligence to), **prospect scoring** (who needs it),
> **SQLite storage**, a **daily Telegram brief**, and a themed **dashboard**.

## What it does

1. **Scrapes** — two engines:
   - `hri/hotel_sites.py` — every hotel's *own* website. Datacenter-friendly
     (no WAF): pulls emails, phones, street addresses, schema.org fields from
     the homepage + contact pages. This is the channel that fills the CRM.
   - `hri/scraper.py` — Booking.com OTA engine via Playwright for when you run
     from a residential IP / laptop / proxy (Booking WAF-challenges datacenter
     IPs). No paid actor required.
2. **Stores** — SQLite (`hotels`, `contacts`, `rates`, `runs`, `prospects`),
   schema small enough to query by hand.
3. **Understands who needs it** — `hri/prospects.py` scores each hotel 0–100
   (independent? right-size? mid-scale stars? dense micro-market? contactable?
   live data flowing?) → `hot / warm / watch` tiers with transparent signals.
4. **Reports** — daily Telegram brief + `run.py report`.
5. **Shows** — `run.py dashboard` → ivory/green/gold finance-dashboard UI
   (palette after @_code_and_chill_'s finance & payroll reel):
   greeting header, KPI cards, grouped rate chart (green up / coral down),
   prospect panel, comp-set contact table, run log.

## Quick start

```bash
git clone https://github.com/Pablodd1/hotel-rate-intelligence.git
cd hotel-rate-intelligence
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # add --break-system-packages on Debian/Ubuntu root

cp config.example.json config.json       # adjust market / stay / telegram
python3 run.py init-db
python3 run.py seed                      # 20 real Miami Beach boutique hotels
python3 run.py collect                   # contacts + best-effort rates + scoring
python3 run.py dashboard                 # http://127.0.0.1:8317
```

Cron it (daily 6 AM):

```
0 6 * * * cd /path/to/hotel-rate-intelligence && python3 run.py collect && python3 run.py report --send
```

## Manual rate ingest

Revenue managers can POST their own BAR:

```bash
curl -X POST localhost:8317/api/rates -d '{"hotel_id":1,"nightly_price":289,"room_type":"King Ocean"}'
```

## Config

See `config.example.json`. `sources.hotel_sites` works everywhere;
`sources.ota` also runs the Playwright Booking engine (set to `true` from a
clean network). Polite delays, timeouts and page caps live under `collector`.

## Upstream credits (the repos this upgrades)

The OSS scraper scene around this use case, studied and consolidated here:

| Repo | What it contributed |
|---|---|
| `omkarcloud/booking-scraper` | 4-endpoint API surface design (search/details/reviews/autocomplete) |
| `flatrow-data-studio/booking-scraper-python` | price-tracker diff pattern (`previous → current`) |
| `PRO100CHOK/booking-com-hotels-prices-reviews-scraper-python` | competitive-set audit framing |
| `ScrapingBee/google-hotels-api` | multi-OTA rate-ladder concept |

Their gap: all lean on **paid** Apify actors and stop at rates. HRI's delta:
contact capture from hotel sites, prospect scoring, storage, reports, dashboard —
MIT, self-hosted, zero per-scrape cost.

## Legal / ethics

- Scrape only public pages, respect `robots.txt` where feasible, keep delays
  polite (built in: 2–5s randomized).
- OTA scraping is at your own risk per their ToS; the hotel-own-site channel is
  the intended default and is what the collector relies on.
- Do not store guest data. Only property-level business contacts.

## License

MIT — see LICENSE.
