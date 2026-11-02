"""OTA rate engine (Booking.com via Playwright).

Datacenter IPs are challenged by Booking's WAF (HTTP 202 + empty shell), so
this engine is only enabled with sources.ota=true — run it from a residential
connection, a laptop, or behind a proxy. The collector degrades gracefully:
when the engine is unavailable it logs the reason and keeps going with the
direct/manual sources.

This module exists so the same collector that fills contacts can fill OTA
rates the moment it runs from a clean network — no paid actor required.
"""
import json, os, random, tempfile, time


def scrape_booking_rates(market, stay, cfg, log=print):
    """Return list of hotel dicts scraped from Booking.com search, or raise."""
    from playwright.sync_api import sync_playwright  # optional dep

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        ctx = browser.new_context(
            locale="en-US", timezone_id="America/New_York",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
            viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto("https://www.booking.com/", wait_until="load", timeout=60000)
        for sel in ("#onetrust-accept-btn-handler", "button:has-text('Accept')"):
            btn = page.query_selector(sel)
            if btn:
                btn.click()
                page.wait_for_timeout(1500)
                break
        page.fill('input[name="ss"]', market)
        page.wait_for_timeout(2000)
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_selector('[data-testid="property-card"]', timeout=30000)

        # infinite-ish scroll, capped
        for _ in range(6):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(2000)

        cards = page.query_selector_all('[data-testid="property-card"]')
        log(f"    OTA: {len(cards)} property cards")
        for card in cards[: cfg["collector"]["max_hotels_per_run"]]:
            try:
                name_el = card.query_selector('[data-testid="title"]')
                price_el = card.query_selector('[data-testid="price-and-discounted-price"], .f6431b446c.fbd1d3018c.fbdbe5b3bf')
                score_el = card.query_selector('[data-testid="review-score"] div:first-child')
                link_el = card.query_selector('a[data-testid="title-link"], a[href*="/hotel/"]')
                link = (link_el.get_attribute("href") if link_el else "") or ""
                results.append({
                    "name": name_el.inner_text().strip() if name_el else "",
                    "nightly_price": _parse_price(price_el.inner_text() if price_el else ""),
                    "review_score": float(score_el.inner_text().split()[0]) if score_el and score_el.inner_text().split()[0].replace(".", "").isdigit() else None,
                    "booking_url": link.split("?")[0],
                })
            except Exception:
                continue
        browser.close()
    return results


def _parse_price(text):
    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None
