"""Verified Contact, PMS/Booking Engine & Social Discovery from Hotel Websites (`hri/hotel_sites.py`).

STRICT ZERO-GUESSING DESIGN:
- Extracts emails, phones, addresses, social links, and booking engine signatures from live HTML.
- Verifies EVERY extracted email domain with a live DNS MX lookup (`nslookup -type=mx`).
- Never guesses emails or social handles from templates.
"""
import random
import re
import subprocess
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cr

from .db import normalize_contact_value

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}")
ADDRESS_RE = re.compile(
    r"\d{2,5}\s+(?:N\.?|S\.?|E\.?|W\.?|North|South|East|West)?\s*"
    r"(?:Ocean|Collins|Washington|Indian Creek|Pine Tree|Island|James|Drexel|Espa[nñ]ola|Lincoln|Meridian|Alton|Biscayne|Bayshore|20th|21st|41st|79th)"
    r"[A-Za-z0-9.'\-\s,]{2,45}(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Terrace|Ter|Causeway)\b\.?",
    re.I,
)
SKIP_EMAIL_DOMAINS = {
    "example.com", "sentry.io", "wixpress.com", "schema.org", "1.4.0",
    "domain.com", "email.com", "yoursite.com", "cloudflare.com", "googleapis.com",
    "w3.org", "latofonts.com", "mysite.com", "placeholder.com",
}
SKIP_EMAIL_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".js", ".css", ".woff", ".woff2")
CONTACT_HINTS = (
    "contact", "about", "location", "directions", "meet", "team", "staff",
    "management", "leadership", "events", "press", "reservations", "groups",
    "weddings", "concierge", "careers", "jobs", "rooms", "front-desk", "faq",
    "privacy", "terms",
)


def classify_department(kind: str, value: str, context: str = "", person_title: str = "") -> str:
    """Classify a hotel email, phone, or person into a hospitality operating department."""
    blob = f"{(value or '').split('@')[0] if kind == 'email' else (value or '')} {context or ''} {person_title or ''}".lower()
    if any(k in blob for k in ("night audit", "nightaudit", "overnight", "audit")):
        return "night_audit"
    if any(k in blob for k in ("revenue", "yield", "pricing", "distribution")):
        return "revenue_mgmt"
    if any(k in blob for k in ("general manager", "managing director", "gm@", "gm ", "owner", "founder", "ceo", "coo", "principal", "president", "director of operations")):
        return "gm_executive"
    if any(k in blob for k in ("reserv", "booking", "book@")):
        return "reservations"
    if any(k in blob for k in ("front desk", "frontdesk", "front office", "frontoffice", "fd@", "mod", "manager on duty", "director of rooms", "rooms division", "guest services", "reception")):
        return "front_office_mod"
    if any(k in blob for k in ("housekeep", "hk ", "maintenance", "engineering")):
        return "housekeeping_ops"
    if any(k in blob for k in ("concierge", "vip", "bell")):
        return "concierge"
    if any(k in blob for k in ("sale", "group", "event", "meet", "wed", "cater", "mice", "ventas", "marketing", "pr@")):
        return "sales_groups"
    return "general_info"

BOOKING_ENGINE_SIGNATURES = [
    ("Cloudbeds", ("cloudbeds.com", "hotels.cloudbeds.com")),
    ("Mews", ("mews.com", "app.mews.com")),
    ("SynXis / Sabre", ("synxis.com", "be.synxis.com")),
    ("TravelClick / iHotelier", ("travelclick.com", "ihotelier.com", "reservations.travelclick")),
    ("SiteMinder / Little Hotelier", ("siteminder.com", "thebookingbutton.com", "littlehotelier.com")),
    ("SimpleBooking", ("simplebooking.it", "simplebooking.travel")),
    ("HotelRunner", ("hotelrunner.com",)),
    ("StayNTouch", ("stayntouch.com",)),
    ("Marriott / CRS", ("marriott.com", "editionhotels.com")),
    ("Hyatt CRS", ("hyatt.com",)),
]

_MX_CACHE = {}


def verify_domain_mx(domain: str) -> bool:
    """Verify via live DNS MX query (with fallback resolver) that a domain accepts inbound email."""
    dom = (domain or "").strip().lower()
    if not dom or "." not in dom:
        return False
    if dom in _MX_CACHE:
        return _MX_CACHE[dom]
    had_timeout = False
    for cmd in (["nslookup", "-type=mx", dom, "8.8.8.8"], ["nslookup", "-type=mx", dom]):
        try:
            out = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=6,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            txt = (out.stdout or "").lower()
            if ("mail exchanger" in txt) or ("mx preference" in txt):
                _MX_CACHE[dom] = True
                return True
        except Exception:
            had_timeout = True
    if not had_timeout:
        _MX_CACHE[dom] = False
    return False


def verify_email_mx(email_addr: str) -> bool:
    if not email_addr or "@" not in email_addr:
        return False
    dom = email_addr.split("@", 1)[1].lower()
    if dom in SKIP_EMAIL_DOMAINS or email_addr.endswith(SKIP_EMAIL_EXTS):
        return False
    return verify_domain_mx(dom)


def detect_booking_engine(html: str) -> str:
    low = (html or "").lower()
    for label, markers in BOOKING_ENGINE_SIGNATURES:
        if any(m in low for m in markers):
            return label
    return ""


def _fetch(url, timeout):
    r = cr.get(url, impersonate="chrome", timeout=timeout, allow_redirects=True,
               headers={"Accept-Language": "en-US,en;q=0.9"})
    r.raise_for_status()
    return r.text, r.url


def _extract(html, page_url):
    soup = BeautifulSoup(html, "lxml")
    emails, phones, addresses, instas, linkedins = set(), set(), set(), set(), set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        low = href.lower()
        if low.startswith("mailto:"):
            em = normalize_contact_value("email", href)
            if em and verify_email_mx(em):
                emails.add(em)
        elif low.startswith("tel:"):
            ph = normalize_contact_value("phone", href)
            if ph:
                phones.add(ph)
        elif "instagram.com/" in low:
            m = re.search(r"instagram\.com/([A-Za-z0-9_.]{2,35})", href, re.I)
            if m and m.group(1).lower() not in {"p", "reel", "explore", "stories"}:
                instas.add("@" + m.group(1))
        elif "linkedin.com/company/" in low or "linkedin.com/in/" in low:
            linkedins.add(href.split("?")[0])

    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S | re.I):
        chunk = m.group(1)
        for key, kind, sink in (("telephone", "phone", phones), ("email", "email", emails), ("streetAddress", "address", addresses)):
            for v in re.findall(rf'"{key}"\s*:\s*"([^"]+)"', chunk):
                clean = normalize_contact_value(kind, v)
                if clean:
                    if kind == "email" and not verify_email_mx(clean):
                        continue
                    sink.add(clean)

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)

    for e in EMAIL_RE.findall(text):
        em = normalize_contact_value("email", e)
        if em and verify_email_mx(em):
            emails.add(em)
    for p in PHONE_RE.findall(text):
        ph = normalize_contact_value("phone", p)
        if ph:
            phones.add(ph)
    for a in ADDRESS_RE.findall(text):
        ad = normalize_contact_value("address", a)
        if ad:
            addresses.add(ad)

    return emails, phones, addresses, instas, linkedins


def discover_pages(base_html, base_url, max_extra):
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
    """Crawl live hotel website; return strictly verified contacts + detected booking_engine & http_status."""
    result = {
        "email": set(), "phone": set(), "address": set(),
        "instagram": set(), "linkedin": set(),
        "booking_engine": "", "website_status": "unknown", "resolved_url": "",
    }
    website = (hotel.get("website") or "").strip()
    if not website:
        return result
    tmo = min(10, cfg.get("collector", {}).get("request_timeout_sec", 10))
    lo, hi = cfg.get("collector", {}).get("polite_delay_sec", [0.2, 0.5])
    try:
        html, final_url = _fetch(website, tmo)
        result["website_status"] = "http_200"
        result["resolved_url"] = final_url
    except Exception as e:
        result["website_status"] = "unreachable"
        log(f"    ! {website}: {type(e).__name__} {str(e)[:80]}")
        return result

    pages = [(final_url, html)]
    max_extra = cfg.get("collector", {}).get("max_contact_pages_per_hotel", 2)
    for url in discover_pages(html, final_url, max_extra):
        time.sleep(random.uniform(lo, hi) * 0.4)
        try:
            p_html, p_url = _fetch(url, tmo)
            pages.append((p_url, p_html))
        except Exception:
            continue

    seen_vals = {k: set() for k in ("email", "phone", "address", "instagram", "linkedin")}
    for url, page_html in pages:
        if not result["booking_engine"]:
            eng = detect_booking_engine(page_html)
            if eng:
                result["booking_engine"] = eng
        em, ph, ad, ig, li = _extract(page_html, url)
        ctx = "homepage" if url == final_url else urlparse(url).path
        for kind, vals in (("email", em), ("phone", ph), ("address", ad), ("instagram", ig), ("linkedin", li)):
            for val in vals:
                if val not in seen_vals[kind]:
                    seen_vals[kind].add(val)
                    result[kind].add((val, ctx, url))

    log(f"    ✓ {hotel['name']}: {len(result['email'])} MX-verified emails, {len(result['phone'])} phones, {len(result['address'])} addr")
    return result
