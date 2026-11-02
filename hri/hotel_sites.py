"""Contact extraction from a hotel's OWN website.

This is the channel that works from datacenter IPs: hotel sites sit on plain
hosting with no WAF. We fetch the homepage + likely contact-ish pages and pull
phones, emails, street addresses and schema.org fields.

Polite by design: few pages, randomized delay, clear timeouts, no brute force.
"""
import random, re, time
from urllib.parse import urljoin, urlparse

from curl_cffi import requests as cr
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}")
ADDRESS_RE = re.compile(r"\d{1,6}\s+[A-Z][A-Za-z0-9.'\-\s]{2,40}(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Terrace|Ter)\b\.?")
SKIP_EMAIL_DOMAINS = {"example.com", "sentry.io", "wixpress.com", "schema.org", "1.4.0"}
CONTACT_HINTS = ("contact", "about", "location", "directions", "meet", "team", "staff", "management")


def _fetch(url, timeout):
    r = cr.get(url, impersonate="chrome", timeout=timeout,
               headers={"Accept-Language": "en-US,en;q=0.9"})
    r.raise_for_status()
    return r.text


def _extract(html, page_url):
    """Pull contacts from one page."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)

    emails, phones, addresses = set(), set(), set()

    # mailto: links are the strongest email signal
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().startswith("mailto:"):
            emails.add(href.split(":", 1)[1].split("?")[0].strip())
        if href.lower().startswith("tel:"):
            phones.add(href.split(":", 1)[1].strip())

    for e in EMAIL_RE.findall(text):
        if not any(e.lower().endswith("@" + d) for d in SKIP_EMAIL_DOMAINS):
            emails.add(e)
    for p in PHONE_RE.findall(text):
        phones.add(p.strip())
    for a in ADDRESS_RE.findall(text):
        addresses.add(" ".join(a.split()))

    # schema.org Hotel fields (name/address/telephone often present)
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S | re.I):
        chunk = m.group(1)
        for key, sink in (("telephone", phones), ("email", emails)):
            for v in re.findall(rf'"{key}"\s*:\s*"([^"]+)"', chunk):
                sink.add(v.strip())
    return emails, phones, addresses


def discover_pages(base_html, base_url, max_extra):
    """Find contact-ish internal pages from the homepage."""
    soup = BeautifulSoup(base_html, "lxml")
    host = urlparse(base_url).netloc.replace("www.", "")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"].lower().split("?")[0].rstrip("/")
        if any(h in href for h in CONTACT_HINTS):
            full = urljoin(base_url, a["href"])
            h = urlparse(full).netloc.replace("www.", "")
            if h == host and full not in seen:
                seen.add(full)
                out.append(full)
        if len(out) >= max_extra:
            break
    return out


def scrape_hotel_contacts(hotel, cfg, log=print):
    """Return dict(kind -> set) for one hotel. Never raises."""
    result = {"email": set(), "phone": set(), "address": set()}
    website = hotel.get("website")
    if not website:
        return result
    tmo = cfg["collector"]["request_timeout_sec"]
    lo, hi = cfg["collector"]["polite_delay_sec"]
    try:
        html = _fetch(website, tmo)
    except Exception as e:
        log(f"    ! {website}: {type(e).__name__} {str(e)[:80]}")
        return result

    pages = [(website, html)]
    for url in discover_pages(html, website, cfg["collector"]["max_contact_pages_per_hotel"]):
        time.sleep(random.uniform(lo, hi))
        try:
            pages.append((url, _fetch(url, tmo)))
        except Exception:
            continue

    for url, html in pages:
        em, ph, ad = _extract(html, url)
        ctx = "homepage" if url == website else urlparse(url).path
        result["email"] |= {(e, ctx) for e in em}
        result["phone"] |= {(p, ctx) for p in ph}
        result["address"] |= {(a, ctx) for a in ad}

    log(f"    ✓ {hotel['name']}: {len(result['email'])} emails, {len(result['phone'])} phones, {len(result['address'])} addresses")
    return result
