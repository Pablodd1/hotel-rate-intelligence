"""Contact extraction from a hotel's OWN website.

This is the channel that works from datacenter IPs: hotel sites sit on plain
hosting with no WAF. We fetch the homepage + likely contact-ish pages and pull
phones, emails, street addresses, social links, booking engine signatures,
and schema.org fields.

Polite by design: few pages, randomized delay, clear timeouts, no brute force.
"""
import random, re, time
from urllib.parse import urljoin, urlparse

from curl_cffi import requests as cr
from bs4 import BeautifulSoup

from .db import normalize_contact_value

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}")
ADDRESS_RE = re.compile(
    r"\d{2,5}\s+(?:Ocean|Collins|Washington|Indian Creek|Pine Tree|Island|James|Drexel|Espa[nñ]ola|Lincoln|Meridian|Alton|20th|21st|41st|79th)"
    r"[A-Za-z0-9.'\-\s,]{2,45}(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Terrace|Ter|Causeway)\b\.?",
    re.I,
)
SKIP_EMAIL_DOMAINS = {
    "example.com", "sentry.io", "wixpress.com", "schema.org", "1.4.0",
    "domain.com", "email.com", "yoursite.com", "cloudflare.com", "googleapis.com"
}
SKIP_EMAIL_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".js", ".css")
CONTACT_HINTS = ("contact", "about", "location", "directions", "meet", "team", "staff", "management", "events", "press")


def _fetch(url, timeout):
    r = cr.get(url, impersonate="chrome", timeout=timeout,
               headers={"Accept-Language": "en-US,en;q=0.9"})
    r.raise_for_status()
    return r.text


def _extract(html, page_url):
    """Pull contacts from one page."""
    soup = BeautifulSoup(html, "lxml")

    emails, phones, addresses = set(), set(), set()

    # mailto: and tel: links are the strongest signal
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        low = href.lower()
        if low.startswith("mailto:"):
            em = normalize_contact_value("email", href)
            if em and not em.endswith(SKIP_EMAIL_EXTS) and not any(em.endswith("@" + d) for d in SKIP_EMAIL_DOMAINS):
                emails.add(em)
        elif low.startswith("tel:"):
            ph = normalize_contact_value("phone", href)
            if ph:
                phones.add(ph)

    # schema.org Hotel fields (name/address/telephone/email often present)
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S | re.I):
        chunk = m.group(1)
        for key, kind, sink in (("telephone", "phone", phones), ("email", "email", emails), ("streetAddress", "address", addresses)):
            for v in re.findall(rf'"{key}"\s*:\s*"([^"]+)"', chunk):
                clean = normalize_contact_value(kind, v)
                if clean:
                    sink.add(clean)

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)

    for e in EMAIL_RE.findall(text):
        em = normalize_contact_value("email", e)
        if em and not em.endswith(SKIP_EMAIL_EXTS) and not any(em.endswith("@" + d) for d in SKIP_EMAIL_DOMAINS):
            emails.add(em)
    for p in PHONE_RE.findall(text):
        ph = normalize_contact_value("phone", p)
        if ph:
            phones.add(ph)
    for a in ADDRESS_RE.findall(text):
        ad = normalize_contact_value("address", a)
        if ad:
            addresses.add(ad)

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
    """Return dict(kind -> set of (value, ctx)) for one hotel. Never raises."""
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

    seen_vals = {"email": set(), "phone": set(), "address": set()}
    for url, page_html in pages:
        em, ph, ad = _extract(page_html, url)
        ctx = "homepage" if url == website else urlparse(url).path
        for val in em:
            if val not in seen_vals["email"]:
                seen_vals["email"].add(val)
                result["email"].add((val, ctx))
        for val in ph:
            if val not in seen_vals["phone"]:
                seen_vals["phone"].add(val)
                result["phone"].add((val, ctx))
        for val in ad:
            if val not in seen_vals["address"]:
                seen_vals["address"].add(val)
                result["address"].add((val, ctx))

    log(f"    ✓ {hotel['name']}: {len(result['email'])} emails, {len(result['phone'])} phones, {len(result['address'])} addresses")
    return result
