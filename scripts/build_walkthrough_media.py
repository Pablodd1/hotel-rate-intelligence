#!/usr/bin/env python3
"""
Build the complete HotelRateIntel video, reel, screenshot, and live screen-recording media pack.

Executes real Playwright interactions against the running HotelRateIntel app, synthesizes
neural voiceover with WordBoundary timestamps, generates ducked ambient music + transition SFX,
renders a 1920x1080 narrated step-by-step walkthrough MP4, and runs the 60fps 1080x1920
ai-producer QC pipeline for two vertical social media reels.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

# Reuse the verified ai-video-producer stages directly (no duplicated audio/music/QC code)
PRODUCER_ROOT = Path(r"C:\Users\jasme\ai-video-producer")
sys.path.insert(0, str(PRODUCER_ROOT / "pipeline"))

from music import run_music, synthesize_music_bed  # type: ignore  # noqa: E402
from qc import run_qc  # type: ignore  # noqa: E402
from render import build_mastered_audio, run_render  # type: ignore  # noqa: E402
from scenes import build_srt_from_words, run_scenes  # type: ignore  # noqa: E402
from voice import generate_edge_neural_with_timestamps, probe_audio_duration, run_voice  # type: ignore  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = os.environ.get("HRI_BASE_URL", "http://127.0.0.1:8317")
MEDIA_ROOT = REPO_ROOT / "media-pack"
SHOTS_DIR = MEDIA_ROOT / "screenshots"
CLIPS_DIR = MEDIA_ROOT / "screen-recordings"
VIDEOS_DIR = MEDIA_ROOT / "videos"
REELS_DIR = MEDIA_ROOT / "reels"
TMP_DIR = MEDIA_ROOT / "_tmp"
REEL_ASSETS_DIR = MEDIA_ROOT / "_reel_assets"

VOICE_NAME = "en-US-ChristopherNeural"
VOICE_RATE = "+8%"

CURSOR_INIT_JS = r"""
(() => {
  if (window.__hriCursorInstalled) return;
  window.__hriCursorInstalled = true;

  const style = document.createElement('style');
  style.textContent = `
    #hri-demo-cursor {
      position: fixed; left: 960px; top: 540px; width: 28px; height: 28px;
      pointer-events: none; z-index: 999999; transform: translate(-4px, -4px);
      transition: left 0.42s cubic-bezier(.22,1,.36,1), top 0.42s cubic-bezier(.22,1,.36,1);
      filter: drop-shadow(0 4px 10px rgba(15, 23, 42, 0.45));
    }
    #hri-demo-ripple {
      position: fixed; width: 44px; height: 44px; border-radius: 50%;
      border: 3px solid #2563EB; background: rgba(56, 189, 248, 0.22);
      pointer-events: none; z-index: 999998; opacity: 0;
      transform: translate(-50%, -50%) scale(0.4);
      transition: transform 0.38s ease-out, opacity 0.38s ease-out;
    }
    #hri-demo-ripple.pop {
      opacity: 1; transform: translate(-50%, -50%) scale(1.25);
    }
    .hri-demo-focus {
      outline: 3px solid #38BDF8 !important;
      outline-offset: 4px !important;
      box-shadow: 0 0 0 8px rgba(56, 189, 248, 0.22) !important;
      transition: all 0.25s ease !important;
    }
  `;
  document.head.appendChild(style);

  const cursor = document.createElement('div');
  cursor.id = 'hri-demo-cursor';
  cursor.innerHTML = `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M4 3L22 14.5L13.6 16.5L10.2 24.5L4 3Z" fill="#0F172A" stroke="#FFFFFF" stroke-width="2" stroke-linejoin="round"/>
  </svg>`;
  document.body.appendChild(cursor);

  const ripple = document.createElement('div');
  ripple.id = 'hri-demo-ripple';
  document.body.appendChild(ripple);

  window.__hriMoveCursor = (sel, clickEffect = false) => {
    const el = typeof sel === 'string' ? document.querySelector(sel) : null;
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const x = Math.max(16, Math.min(window.innerWidth - 16, r.left + r.width * 0.5));
    const y = Math.max(16, Math.min(window.innerHeight - 16, r.top + r.height * 0.5));
    cursor.style.left = x + 'px';
    cursor.style.top = y + 'px';
    document.querySelectorAll('.hri-demo-focus').forEach(n => n.classList.remove('hri-demo-focus'));
    el.classList.add('hri-demo-focus');
    if (clickEffect) {
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      ripple.classList.remove('pop');
      void ripple.offsetWidth;
      ripple.classList.add('pop');
      setTimeout(() => ripple.classList.remove('pop'), 420);
    }
    return { x, y };
  };

  window.__hriClearFocus = () => {
    document.querySelectorAll('.hri-demo-focus').forEach(n => n.classList.remove('hri-demo-focus'));
  };

  window.__hriSetCursorVisible = (vis) => {
    cursor.style.opacity = vis ? '1' : '0';
  };
})();
"""


def snap_clean_screenshot(page: Page, path: Path) -> None:
    """Capture crisp static PNG screenshot without overlay focus outlines or pointer hiding text."""
    page.evaluate("window.__hriClearFocus && window.__hriClearFocus(); window.__hriSetCursorVisible && window.__hriSetCursorVisible(false);")
    page.wait_for_timeout(120)
    page.screenshot(path=str(path))
    page.evaluate("window.__hriSetCursorVisible && window.__hriSetCursorVisible(true);")


def run_cmd(cmd: List[str], cwd: Path | None = None) -> None:
    """Run subprocess cleanly raising readable errors on failure."""
    res = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(cmd)}\nSTDERR:\n{res.stderr}")


def ensure_dirs() -> None:
    for d in (SHOTS_DIR, CLIPS_DIR, VIDEOS_DIR, REELS_DIR, TMP_DIR, REEL_ASSETS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def install_cursor(page: Page) -> None:
    page.evaluate(CURSOR_INIT_JS)


def focus_move(page: Page, selector: str, click: bool = False, settle: float = 0.7) -> None:
    """Scroll element comfortably into view, glide demo cursor onto it, and optionally click."""
    loc = page.locator(selector).first
    if loc.count() == 0:
        return
    try:
        loc.scroll_into_view_if_needed(timeout=2500)
    except Exception:
        pass
    page.wait_for_timeout(200)
    page.evaluate("(sel) => window.__hriMoveCursor && window.__hriMoveCursor(sel, false)", selector)
    page.wait_for_timeout(int(settle * 1000))
    if click:
        page.evaluate("(sel) => window.__hriMoveCursor && window.__hriMoveCursor(sel, true)", selector)
        loc.click(force=True)
        page.wait_for_timeout(450)


def open_clean_recording_page(
    browser: Browser,
    raw_dir: Path,
    url: str,
    ready_selector: str,
    width: int = 1920,
    height: int = 1080,
) -> Tuple[BrowserContext, Page, float]:
    """
    Open a recorded Playwright context, wait until page UI hydrates completely,
    install animated cursor HUD, and return the initial load trim offset in seconds
    so final clips never contain white startup frames.
    """
    t0 = time.monotonic()
    ctx = browser.new_context(
        viewport={"width": width, "height": height},
        record_video_dir=str(raw_dir),
        record_video_size={"width": width, "height": height},
        device_scale_factor=1,
    )
    page = ctx.new_page()
    page.goto(url, wait_until="networkidle", timeout=25000)
    page.wait_for_selector(ready_selector, timeout=15000)
    page.wait_for_timeout(650)
    install_cursor(page)
    trim_start = max(0.25, time.monotonic() - t0 - 0.1)
    return ctx, page, trim_start


def finalize_recording(ctx: BrowserContext, page: Page, trim_start: float, out_mp4: Path) -> Path:
    """Close Playwright recording context cleanly and transcode WebM starting at trim_start to MP4."""
    vid = page.video
    page.close()
    ctx.close()
    if vid is None:
        raise RuntimeError(f"Playwright video handle missing for {out_mp4.name}")
    webm_path = Path(vid.path())
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{trim_start:.2f}",
            "-i",
            str(webm_path),
            "-vf",
            "scale=1920:1080:flags=lanczos,fps=30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(out_mp4),
        ]
    )
    return out_mp4


def step_01_action(browser: Browser) -> Tuple[BrowserContext, Page, float]:
    """Step 1: Open HotelRateIntel homepage and run interactive ROI calculator."""
    ctx, page, trim_start = open_clean_recording_page(
        browser, TMP_DIR / "rec1", f"{BASE_URL}/website", "#roiRooms"
    )
    page.wait_for_timeout(600)
    focus_move(page, "#heroHotelPicker", settle=0.6)
    focus_move(page, "#roiRooms", click=True, settle=0.55)
    page.locator("#roiRooms").fill("60")
    page.wait_for_timeout(400)
    focus_move(page, "#roiAdr", click=True, settle=0.55)
    page.locator("#roiAdr").fill("265")
    page.wait_for_timeout(500)
    focus_move(page, "#roiTotalMo", settle=0.9)
    snap_clean_screenshot(page, SHOTS_DIR / "step_01_hero_roi.png")
    page.wait_for_timeout(500)
    return ctx, page, trim_start


def step_02_action(browser: Browser) -> Tuple[BrowserContext, Page, float]:
    """Step 2: Showcase hospitality benefits (Make Money + Save Money) & 5-column comparison."""
    ctx, page, trim_start = open_clean_recording_page(
        browser, TMP_DIR / "rec2", f"{BASE_URL}/website#industry-roi", "#whyUsTableBody tr"
    )
    page.evaluate("document.querySelector('#industry-roi').scrollIntoView({behavior:'instant'})")
    page.wait_for_timeout(700)
    focus_move(page, "#industry-roi .card:nth-child(1)", settle=0.8)
    focus_move(page, "#industry-roi .card:nth-child(2)", settle=0.8)
    page.evaluate("document.querySelector('table.cmp').scrollIntoView({behavior:'smooth', block:'center'})")
    page.wait_for_timeout(900)
    focus_move(page, "table.cmp", settle=0.8)
    snap_clean_screenshot(page, SHOTS_DIR / "step_02_industry_benefits_comparison.png")
    page.wait_for_timeout(500)
    return ctx, page, trim_start


def step_03_action(browser: Browser) -> Tuple[BrowserContext, Page, float]:
    """Step 3: Live Hotel Website Auditor, Decision Assistant & OTA/Corridor SVGs."""
    ctx, page, trim_start = open_clean_recording_page(
        browser, TMP_DIR / "rec3", f"{BASE_URL}/website#auditor", "#auditOtaSvgWrap svg"
    )
    page.evaluate("document.querySelector('#auditor').scrollIntoView({behavior:'instant'})")
    page.wait_for_timeout(700)
    focus_move(page, "#auditHotelSelect", click=True, settle=0.6)
    opts = page.locator("#auditHotelSelect option").count()
    if opts > 1:
        val2 = page.locator("#auditHotelSelect option").nth(1).get_attribute("value")
        if val2:
            page.select_option("#auditHotelSelect", val2)
    focus_move(page, "#btnRunAudit", click=True, settle=0.7)
    page.wait_for_timeout(1200)
    focus_move(page, "#daVerdict", settle=0.8)
    focus_move(page, "#auditOtaSvgWrap", settle=0.8)
    focus_move(page, "#auditCompSvgWrap", settle=0.8)
    snap_clean_screenshot(page, SHOTS_DIR / "step_03_live_website_auditor.png")
    page.wait_for_timeout(500)
    return ctx, page, trim_start


def step_04_action(browser: Browser) -> Tuple[BrowserContext, Page, float]:
    """Step 4: Open Isolated Client Portal (/portal?demo_hotel=1) Comp-Set & Strategy."""
    ctx, page, trim_start = open_clean_recording_page(
        browser, TMP_DIR / "rec4", f"{BASE_URL}/portal?demo_hotel=1", "#clientCompTableBody tr"
    )
    page.wait_for_timeout(750)
    focus_move(page, "#kpiMyBar", settle=0.65)
    focus_move(page, "#kpiHoursSaved", settle=0.65)
    focus_move(page, "#kpiRecAction", settle=0.75)
    focus_move(page, "#portalOtaSvgBox", settle=0.7)
    snap_clean_screenshot(page, SHOTS_DIR / "step_04_portal_bar_compset.png")
    page.evaluate("document.querySelector('#clientCompTableBody').scrollIntoView({behavior:'smooth', block:'center'})")
    page.wait_for_timeout(1200)
    focus_move(page, "#clientCompTableBody tr:first-child", settle=0.75)
    return ctx, page, trim_start


def step_05_action(browser: Browser) -> Tuple[BrowserContext, Page, float]:
    """Step 5: Portal Tab 2 (Pricing Memory & Tags) & Tab 3 (Overnight Courtesy Call Desk)."""
    ctx, page, trim_start = open_clean_recording_page(
        browser, TMP_DIR / "rec5", f"{BASE_URL}/portal?demo_hotel=1", "#cbtn-memory"
    )
    focus_move(page, "#cbtn-memory", click=True, settle=0.7)
    page.wait_for_timeout(650)
    focus_move(page, "#tagLabelInput", click=True, settle=0.5)
    page.locator("#tagLabelInput").fill("Weekend Compression Rival - Watch Agoda")
    focus_move(page, "#tagNoteInput", click=True, settle=0.5)
    page.locator("#tagNoteInput").fill("Hold BAR within $10 when neighbor occupancy > 80%")
    snap_clean_screenshot(page, SHOTS_DIR / "step_05_portal_memory_tags.png")
    page.wait_for_timeout(600)

    focus_move(page, "#cbtn-calls", click=True, settle=0.7)
    page.wait_for_timeout(650)
    focus_move(page, "#callOccInput", click=True, settle=0.5)
    page.locator("#callOccInput").fill("91")
    focus_move(page, "#clientCallsBody", settle=0.7)
    snap_clean_screenshot(page, SHOTS_DIR / "step_06_portal_courtesy_calls.png")
    page.wait_for_timeout(600)

    focus_move(page, "#cbtn-tiers", click=True, settle=0.8)
    page.wait_for_timeout(750)
    return ctx, page, trim_start


def step_06_action(browser: Browser) -> Tuple[BrowserContext, Page, float]:
    """Step 6: Pricing ($0 Free -> $99 Core -> $199 Pro), Free Account Claim & AI Dynamic Pro Consultation."""
    ctx, page, trim_start = open_clean_recording_page(
        browser, TMP_DIR / "rec6", f"{BASE_URL}/website#pricing", "#websiteTiersGrid .card"
    )
    page.evaluate("document.querySelector('#pricing').scrollIntoView({behavior:'instant'})")
    page.wait_for_timeout(750)
    focus_move(page, "#websiteTiersGrid .card:nth-child(2)", settle=0.8)
    focus_move(page, "#register", settle=0.7)
    snap_clean_screenshot(page, SHOTS_DIR / "step_07_pricing_account_claim.png")
    page.wait_for_timeout(500)

    page.evaluate("document.querySelector('#aidynamic-consultation').scrollIntoView({behavior:'smooth'})")
    page.wait_for_timeout(1100)
    focus_move(page, "#aidynamic-consultation .card.dark", settle=0.85)
    page.evaluate("document.querySelector('#blogs').scrollIntoView({behavior:'smooth'})")
    page.wait_for_timeout(1000)
    focus_move(page, "#blogs .card:first-child", settle=0.75)
    page.evaluate("document.querySelector('#aidynamic-consultation').scrollIntoView({behavior:'instant'})")
    snap_clean_screenshot(page, SHOTS_DIR / "step_08_ai_consultation_blogs.png")
    page.wait_for_timeout(500)
    return ctx, page, trim_start


WALKTHROUGH_STEPS: List[Dict[str, Any]] = [
    {
        "clip": "clip_01_hero_calculator.mp4",
        "badge": "STEP 1 OF 6 · INSTANT ROI CALCULATOR",
        "title": "Calculate Monthly Hotel Savings & Direct Revenue",
        "action": step_01_action,
        "narration": (
            "Welcome to HotelRateIntel by AI Dynamic Pro. Start on hotelrateintel dot com by entering your "
            "room count and nightly ADR into the interactive calculator. Instantly see how catching 18 to 44 percent "
            "OTA undercuts and freeing 45 hours of manual tab checking unlocks over 8900 dollars a month in net benefit."
        ),
    },
    {
        "clip": "clip_02_industry_benefits.mp4",
        "badge": "STEP 2 OF 6 · MAKE MONEY & SAVE MONEY",
        "title": "Plug OTA Leaks & Save 45-68 Staff Hrs/Mo",
        "action": step_02_action,
        "narration": (
            "Scroll to Industry Benefits to see both sides of profit. On top line revenue, you catch wholesale leaks "
            "on Agoda or Vio and capture compression ADR lifts during major city events. On cost cuts, "
            "you save 1125 to 1700 dollars a month in payroll versus 450 to 900 dollar legacy rate suites."
        ),
    },
    {
        "clip": "clip_03_live_auditor.mp4",
        "badge": "STEP 3 OF 6 · LIVE WEBSITE AUDITOR",
        "title": "Scan Any Hotel URL + Auto SVG Rate Ladder",
        "action": step_03_action,
        "narration": (
            "Next, test any boutique property in the Live Website Auditor. Select a sample or paste your own hotel URL "
            "and click Scan Website and Rates. HotelRateIntel detects your booking engine stack, exposes any active "
            "OTA undercut in red, draws your live Channel Rate Ladder and Comp-Set SVGs, and drafts an instant email brief."
        ),
    },
    {
        "clip": "clip_04_portal_compset.mp4",
        "badge": "STEP 4 OF 6 · ISOLATED CLIENT PORTAL",
        "title": "6 AM Comp-Set Brief & Actionable BAR Call",
        "action": step_04_action,
        "narration": (
            "Inside your strictly isolated Client Portal, your Reservations and Front Office team sees only your property "
            "and your assigned street comp-set. Review your live BAR versus local average, exact hours saved, "
            "and today's clear Decision Assistant call like Hold BAR or Raise 25 dollars—no spreadsheets required."
        ),
    },
    {
        "clip": "clip_05_portal_memory_calls.mp4",
        "badge": "STEP 5 OF 6 · MEMORY TAGS & CALL DESK",
        "title": "Competitor Memory & Overnight Call-Arounds",
        "action": step_05_action,
        "narration": (
            "Open Tab 2 to store private competitor pricing memory and custom strategy tags so night or afternoon desks "
            "never panic-discount. Then switch to Tab 3, the Courtesy Call Desk, to log overnight front-desk occupancy "
            "checks cleanly—and preview Free 0 dollar, Core 99 dollar, and Pro 199 dollar capabilities live."
        ),
    },
    {
        "clip": "clip_06_pricing_ai_consultation.mp4",
        "badge": "STEP 6 OF 6 · $0 START & $99 AI AUDIT",
        "title": "Start Free or Book Custom AI in 48 Hours",
        "action": step_06_action,
        "narration": (
            "Claim your isolated hotel portal free forever on Tier 1 or unlock daily 6 AM briefs on Core for 99 dollars "
            "a month with zero contract. Need bilingual 24-hour AI voice receptionists or custom hotel workflows built fast? "
            "Book our 99 dollar 48-hour AI Workflow Audit backed by a 2500 dollar per month savings guarantee."
        ),
    },
]


def format_ass_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60.0
    return f"{h}:{m:02d}:{s:05.2f}"


def write_ass_from_words(words: List[Dict[str, Any]], out_ass: Path, width: int = 1920, height: int = 1080) -> None:
    """Create crisp readable lower-third ASS subtitles grouped into 7-word phrases."""
    header = "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: Default,Segoe UI,44,&H00FFFFFF,&H0038BDF8,&H000F172A,&HD80F172A,-1,0,0,0,100,100,0,0,3,14,0,2,120,120,46,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
    )
    events: List[str] = []
    chunk_size = 7
    for i in range(0, len(words), chunk_size):
        chunk = words[i : i + chunk_size]
        if not chunk:
            continue
        st = max(0.0, float(chunk[0]["start"]))
        en = float(chunk[-1]["end"]) + 0.12
        txt = " ".join(w["word"] for w in chunk).replace("{", "").replace("}", "")
        events.append(f"Dialogue: 0,{format_ass_time(st)},{format_ass_time(en)},Default,,0,0,0,,{txt}")
    out_ass.write_text(header + "\n" + "\n".join(events) + "\n", encoding="utf-8")


def render_step_badge_png(step_badge: str, step_title: str, out_png: Path) -> Path:
    """Render a sleek 1920x1080 transparent top-bar PNG overlay via Pillow (immune to FFmpeg fontconfig)."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (1920, 1080), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)

    # Subtle studio glass gradient backdrop + clean rounded bezel for 1800x1012 screen area at (60, 56)
    for y in range(1080):
        c = int(12 + (y / 1080.0) * 14)
        draw.line([(0, y), (1920, y)], fill=(c, c + 8, c + 24, 255))

    try:
        font_badge = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 19)
        font_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 24)
        font_url = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 19)
    except Exception:
        font_badge = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_url = ImageFont.load_default()

    # Dynamically measure step badge pill width so long badges never collide with step title
    b_box = draw.textbbox((0, 0), step_badge, font=font_badge)
    pill_w = (b_box[2] - b_box[0]) + 36
    pill_end = 60 + pill_w
    draw.rounded_rectangle([60, 10, pill_end, 44], radius=17, fill=(37, 99, 235, 255))
    draw.text((78, 15), step_badge, fill=(255, 255, 255, 255), font=font_badge)
    draw.text((pill_end + 18, 12), step_title, fill=(241, 245, 249, 255), font=font_title)

    url_txt = "hotelrateintel.com  ·  AI Dynamic Pro"
    u_box = draw.textbbox((0, 0), url_txt, font=font_url)
    draw.text((1860 - (u_box[2] - u_box[0]), 15), url_txt, fill=(148, 163, 184, 255), font=font_url)

    # Crisp frame outline around video window (60, 54, 1860, 1066)
    draw.rounded_rectangle([58, 52, 1862, 1068], radius=16, outline=(56, 189, 248, 175), width=2)
    img.save(out_png, "PNG")
    return out_png


def sync_clip_to_duration(
    raw_mp4: Path,
    target_dur: float,
    step_badge: str,
    step_title: str,
    out_mp4: Path,
) -> None:
    """Adjust clip timing smoothly to exact spoken duration inside a clean studio frame."""
    info = json.loads(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(raw_mp4)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    src_dur = max(1.0, float(info["format"]["duration"]))
    pts_factor = min(1.35, max(0.75, target_dur / src_dur))
    scaled_dur = src_dur * pts_factor
    extra_pad = max(0.0, target_dur - scaled_dur + 0.05)

    frame_bg = out_mp4.with_suffix(".bg.png")
    render_step_badge_png(step_badge, step_title, frame_bg)

    filter_complex = (
        f"[1:v]setpts={pts_factor:.4f}*PTS,"
        f"tpad=stop_mode=clone:stop_duration={extra_pad:.3f},"
        f"trim=duration={target_dur:.3f},setpts=PTS-STARTPTS,"
        f"scale=1800:1012:flags=lanczos[clip];"
        f"[0:v][clip]overlay=60:54[v]"
    )
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-t",
            f"{target_dur:.3f}",
            "-i",
            str(frame_bg),
            "-i",
            str(raw_mp4),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(out_mp4),
        ]
    )


def build_full_walkthrough_video(step_results: List[Dict[str, Any]]) -> Path:
    """Synthesize neural narration per step, align Playwright clips, burn subtitles & master to -14 LUFS."""
    script_lines = [
        {"line_index": idx, "text": st["narration"]}
        for idx, st in enumerate(WALKTHROUGH_STEPS)
    ]

    voice_dir = TMP_DIR / "walkthrough_voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    voice_mp3 = voice_dir / "voice_full.mp3"

    words = asyncio.run(
        generate_edge_neural_with_timestamps(
            script_lines=script_lines,
            out_mp3=voice_mp3,
            voice_name=VOICE_NAME,
            rate=VOICE_RATE,
        )
    )

    line_files_dir = voice_mp3.parent / "_voice_lines"
    line_durs: List[float] = []
    cut_times: List[float] = []
    running_t = 0.0
    for idx in range(len(WALKTHROUGH_STEPS)):
        lmp3 = line_files_dir / f"line_{idx:02d}.mp3"
        dur = probe_audio_duration(lmp3)
        if idx > 0:
            cut_times.append(round(running_t, 3))
        line_durs.append(dur)
        running_t += dur

    total_voice_dur = probe_audio_duration(voice_mp3)

    # Generate aligned ASS subtitles + external SRT from exact WordBoundary timings
    ass_path = TMP_DIR / "walkthrough.ass"
    write_ass_from_words(words, ass_path, width=1920, height=1080)
    srt_path = VIDEOS_DIR / "walkthrough_captions.srt"
    srt_path.write_text(build_srt_from_words(words, chunk_size=7), encoding="utf-8")

    # Sync each recorded browser clip to its spoken step duration
    synced_clips: List[Path] = []
    for idx, (st, res) in enumerate(zip(WALKTHROUGH_STEPS, step_results)):
        synced_mp4 = TMP_DIR / f"synced_step_{idx:02d}.mp4"
        sync_clip_to_duration(
            raw_mp4=res["raw_mp4"],
            target_dur=line_durs[idx],
            step_badge=st["badge"],
            step_title=st["title"],
            out_mp4=synced_mp4,
        )
        synced_clips.append(synced_mp4)

    concat_list = TMP_DIR / "concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.name}'" for p in synced_clips),
        encoding="utf-8",
    )
    video_joined = TMP_DIR / "walkthrough_joined_nosubs.mp4"
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list.name,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(video_joined),
        ],
        cwd=TMP_DIR,
    )

    # Burn captions using relative filename in cwd=TMP_DIR (avoids Windows C:\ colon filter escaping issues)
    video_subtitled = TMP_DIR / "walkthrough_subtitled.mp4"
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_joined.name,
            "-vf",
            f"ass={ass_path.name}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(video_subtitled),
        ],
        cwd=TMP_DIR,
    )

    # Synthesize cohesive ambient bed + subtle transition SFX cuts, then master audio to -14 LUFS
    music_wav = TMP_DIR / "walkthrough_music.wav"
    music_mp3 = TMP_DIR / "walkthrough_music.mp3"
    half_sec_pulses = [round(k * 0.5, 2) for k in range(int(total_voice_dur * 2))]
    synthesize_music_bed(
        duration_sec=total_voice_dur + 0.5,
        scene_cut_times=cut_times,
        half_sec_pulse_times=half_sec_pulses,
        out_wav=music_wav,
    )
    run_cmd(
        ["ffmpeg", "-y", "-i", str(music_wav), "-c:a", "libmp3lame", "-b:a", "192k", str(music_mp3)]
    )

    master_wav = TMP_DIR / "walkthrough_master_14lufs.wav"
    build_mastered_audio(
        voice_mp3=voice_mp3,
        music_mp3=music_mp3,
        duration=total_voice_dur,
        out_wav=master_wav,
        target_lufs=-14.0,
        music_volume=0.18,
    )

    final_video = VIDEOS_DIR / "hotelrateintel_step_by_step_walkthrough_1080p.mp4"
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_subtitled),
            "-i",
            str(master_wav),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{total_voice_dur:.3f}",
            "-movflags",
            "+faststart",
            str(final_video),
        ]
    )

    # Write clean script transcript & timings
    script_txt = VIDEOS_DIR / "walkthrough_script.txt"
    t_cur = 0.0
    lines_out = ["HotelRateIntel — Complete 1080p Step-by-Step Walkthrough Script", "=" * 64, ""]
    for idx, (st, d) in enumerate(zip(WALKTHROUGH_STEPS, line_durs), 1):
        lines_out.append(f"[{t_cur:05.2f}s - {t_cur+d:05.2f}s] {st['badge']} — {st['title']}")
        lines_out.append(st["narration"])
        lines_out.append("")
        t_cur += d
    script_txt.write_text("\n".join(lines_out), encoding="utf-8")

    return final_video


def capture_vertical_reel_screenshots(browser: Browser) -> Dict[str, Path]:
    """Capture crisp 1000x1040 UI cards of real live HotelRateIntel views for 9:16 Reels."""
    ctx = browser.new_context(viewport={"width": 1000, "height": 1040}, device_scale_factor=1)
    page = ctx.new_page()

    shots: Dict[str, Path] = {}

    def snap(key: str, url: str, setup_js: str | None = None, wait_sel: str = "body") -> None:
        page.goto(url, wait_until="networkidle", timeout=25000)
        page.wait_for_selector("body", timeout=10000)
        page.wait_for_timeout(650)
        if setup_js:
            page.evaluate(setup_js)
            page.wait_for_timeout(450)
        page.wait_for_selector(wait_sel, timeout=15000)
        page.wait_for_timeout(250)
        out = REEL_ASSETS_DIR / f"{key}.png"
        page.screenshot(path=str(out))
        shots[key] = out

    snap("hero", f"{BASE_URL}/website", "window.scrollTo(0, 0);", "#roiRooms")
    snap(
        "calc",
        f"{BASE_URL}/website",
        "document.querySelector('#roiRooms').value='60'; document.querySelector('#roiAdr').value='265'; if(window.recalcRoi) recalcRoi(); document.querySelector('.card.dark').scrollIntoView({behavior:'instant', block:'center'});",
        "#roiTotalMo",
    )
    snap(
        "roi_matrix",
        f"{BASE_URL}/website#industry-roi",
        "document.querySelector('#industry-roi').scrollIntoView({behavior:'instant'});",
        "#whyUsTableBody tr",
    )
    snap(
        "auditor",
        f"{BASE_URL}/website#auditor",
        "document.querySelector('#auditor').scrollIntoView({behavior:'instant'});",
        "#auditOtaSvgWrap svg",
    )
    snap(
        "portal_bar",
        f"{BASE_URL}/portal?demo_hotel=1",
        "window.scrollTo(0, 0);",
        "#clientCompTableBody tr",
    )
    snap(
        "portal_memory",
        f"{BASE_URL}/portal?demo_hotel=1",
        "switchClientTab && switchClientTab('memory'); window.scrollTo(0, 0);",
        "#clientMemoryBody tr",
    )
    snap(
        "portal_calls",
        f"{BASE_URL}/portal?demo_hotel=1",
        "switchClientTab && switchClientTab('calls'); window.scrollTo(0, 0);",
        "#clientCallsBody",
    )
    snap(
        "pricing",
        f"{BASE_URL}/website#pricing",
        "document.querySelector('#pricing').scrollIntoView({behavior:'instant'});",
        "#websiteTiersGrid .card",
    )
    snap(
        "consultation",
        f"{BASE_URL}/website#aidynamic-consultation",
        "document.querySelector('#aidynamic-consultation').scrollIntoView({behavior:'instant'});",
        "#aidynamic-consultation",
    )

    page.close()
    ctx.close()
    return shots


def build_vertical_reels_via_producer(reel_shots: Dict[str, Path]) -> List[Dict[str, Any]]:
    """
    Create two 60fps 1080x1920 social media reels through the installed ai-producer pipeline
    using real vertical Playwright screenshots of HotelRateIntel, running full 12-check QC.
    """
    profile_path = TMP_DIR / "hri_producer_profile.md"
    profile_path.write_text(
        "\n".join(
            [
                "# Profile",
                "Name / brand: HotelRateIntel by AI Dynamic Pro",
                "Niche and audience: Independent 15-75 room boutique hotels & Reservations teams",
                f"Voice: {VOICE_NAME}",
                "Speaking style: short lines, concrete dollar & hour numbers, plain English",
                "Hook rule: name HotelRateIntel and the exact hotel payoff in line 1",
                "Video length: 35-55 seconds, vertical 1080x1920",
                "Call to action (exact words): Comment HOTEL and I'll send you the free audit link.",
                "Words I never use: delve, tapestry, game-changer, unleash, skyrocket, revolutionary, secret weapon, mind-blowing",
                "On-screen style: dark background (#080A0F), white captions (#FFFFFF), one accent colour: #00F0FF",
            ]
        ),
        encoding="utf-8",
    )

    reel_specs = [
        {
            "slug": "hri-reel-step-by-step",
            "out_name": "reel_01_step_by_step_how_to_use_1080x1920.mp4",
            "topic": "How boutique hotels use HotelRateIntel step by step to stop losing 44 percent on OTA undercuts",
            "cta_keyword": "HOTEL",
            "lines": [
                {
                    "tag": "HOOK · HOTELRATEINTEL",
                    "big_word": "STOP LEAKS",
                    "target_url": "https://hotelrateintel.com",
                    "text": "HotelRateIntel stops boutique hotels from losing 44 percent on hidden OTA rate undercuts in four fast steps.",
                    "steps": [
                        ("hero", "STEP 1 · HOTELRATEINTEL.COM", "28%", "42%"),
                        ("calc", "CALCULATE MONTHLY ROI", "72%", "48%"),
                    ],
                },
                {
                    "tag": "STEP 1 · AUDIT URL",
                    "big_word": "SCAN URL",
                    "target_url": "https://hotelrateintel.com/#auditor",
                    "text": "Step one, paste your hotel URL into the live auditor and spot every Vio, Agoda, and Booking undercut.",
                    "steps": [
                        ("auditor", "PASTE URL & SCAN", "52%", "32%"),
                        ("auditor", "SVG OTA RATE LADDER", "60%", "64%"),
                    ],
                },
                {
                    "tag": "STEP 2 · COMP-SET",
                    "big_word": "HOLD BAR",
                    "target_url": "https://hotelrateintel.com/portal",
                    "text": "Step two, open your isolated client portal every morning at six AM to see your Best Available Rate versus local neighbors.",
                    "steps": [
                        ("portal_bar", "ISOLATED CLIENT PORTAL", "30%", "28%"),
                        ("portal_bar", "DECISION ASSISTANT", "74%", "36%"),
                    ],
                },
                {
                    "tag": "STEP 3 · MEMORY",
                    "big_word": "68 HRS",
                    "target_url": "https://hotelrateintel.com/portal",
                    "text": "Step three, track competitor pricing memory and log overnight courtesy calls without wasteful spreadsheets.",
                    "steps": [
                        ("portal_memory", "COMPETITOR MEMORY TAGS", "38%", "44%"),
                        ("portal_calls", "OVERNIGHT CALL DESK", "46%", "46%"),
                    ],
                },
                {
                    "tag": "STEP 4 · $0 START",
                    "big_word": "FREE START",
                    "target_url": "https://hotelrateintel.com/#pricing",
                    "text": "Claim your isolated starter portal at zero dollars per month or scale to automated daily alerts for 99 flat. Comment HOTEL and I'll send you the free audit link.",
                    "steps": [
                        ("pricing", "TIER 1 FREE -> $99 CORE", "50%", "48%"),
                        ("consultation", "$99 48-HR AI AUDIT", "30%", "55%"),
                    ],
                },
            ],
        },
        {
            "slug": "hri-reel-hotel-benefits",
            "out_name": "reel_02_hotel_benefits_save_68_hrs_1080x1920.mp4",
            "topic": "Benefits boutique hotels get from HotelRateIntel: 68 hours saved and +58k direct revenue",
            "cta_keyword": "HOTEL",
            "lines": [
                {
                    "tag": "HOTEL ROI · PAYOFF",
                    "big_word": "+$58K/YR",
                    "target_url": "https://hotelrateintel.com",
                    "text": "HotelRateIntel helps 15 to 75 room hotels recover 58000 dollars a year while saving 68 front-desk hours monthly.",
                    "steps": [
                        ("calc", "NET BENEFIT +$8,959/MO", "68%", "44%"),
                        ("hero", "BOUTIQUE REVENUE ENGINE", "32%", "48%"),
                    ],
                },
                {
                    "tag": "BENEFIT 1 · MAKE MONEY",
                    "big_word": "NO UNDERCUTS",
                    "target_url": "https://hotelrateintel.com/#auditor",
                    "text": "First, catch wholesale OTAs undercutting your direct website rate before guests book third party for fifteen percent commission.",
                    "steps": [
                        ("auditor", "EXPOSE OTA UNDERCUTS", "56%", "52%"),
                        ("roi_matrix", "TOP-LINE REVENUE ENGINE", "32%", "38%"),
                    ],
                },
                {
                    "tag": "BENEFIT 2 · ADR LIFT",
                    "big_word": "+15% ADR",
                    "target_url": "https://hotelrateintel.com/portal",
                    "text": "Second, track Art Basel and Formula One compression weeks so your front desk raises rates instead of selling out cheap.",
                    "steps": [
                        ("portal_bar", "RAISE BAR TARGETS", "78%", "28%"),
                        ("portal_memory", "COMPETITOR MEMORY LOG", "55%", "45%"),
                    ],
                },
                {
                    "tag": "BENEFIT 3 · CUT COST",
                    "big_word": "SAVE $1,700",
                    "target_url": "https://hotelrateintel.com/#industry-roi",
                    "text": "Third, stop paying 1700 dollars monthly in manual morning tab checking or 900 dollars for clunky legacy software.",
                    "steps": [
                        ("roi_matrix", "HEAD-TO-HEAD SAVINGS", "48%", "65%"),
                        ("pricing", "$0 FREE OR $99 CORE", "50%", "48%"),
                    ],
                },
                {
                    "tag": "AI DYNAMIC PRO · MIAMI",
                    "big_word": "$99 AUDIT",
                    "target_url": "https://hotelrateintel.com/#aidynamic-consultation",
                    "text": "Plus book AI Dynamic Pro's 99 dollar 48-hour AI audit for 24-hour bilingual hotel voice receptionists. Comment HOTEL and I'll send you the free audit link.",
                    "steps": [
                        ("consultation", "48-HR CUSTOM AI AUDIT", "26%", "52%"),
                        ("hero", "START FREE AT HOTELRATEINTEL", "44%", "58%"),
                    ],
                },
            ],
        },
    ]

    outputs: List[Dict[str, Any]] = []
    for spec in reel_specs:
        job_dir = PRODUCER_ROOT / "jobs" / spec["slug"]
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
        (job_dir / "assets").mkdir(parents=True, exist_ok=True)

        script_lines = []
        manifest_assets = []
        all_words_count = 0
        for idx, ln in enumerate(spec["lines"]):
            wcount = len(ln["text"].split())
            all_words_count += wcount
            script_lines.append(
                {
                    "line_index": idx,
                    "tag": ln["tag"],
                    "big_word": ln["big_word"],
                    "target_url": ln["target_url"],
                    "text": ln["text"],
                    "word_count": wcount,
                }
            )
            step_entries = []
            primary_rel = None
            for s_idx, (shot_key, label, cx, cy) in enumerate(ln["steps"]):
                dest_rel = f"assets/scene_{idx:02d}_step_{s_idx}.png"
                shutil.copy2(reel_shots[shot_key], job_dir / dest_rel)
                if primary_rel is None:
                    primary_rel = dest_rel
                step_entries.append(
                    {
                        "asset_file": dest_rel,
                        "label": label,
                        "cursor_x": cx,
                        "cursor_y": cy,
                    }
                )
            manifest_assets.append(
                {
                    "scene_index": idx,
                    "asset_file": primary_rel,
                    "steps": step_entries,
                }
            )

        (job_dir / "job.json").write_text(
            json.dumps({"topic": spec["topic"], "slug": spec["slug"]}, indent=2),
            encoding="utf-8",
        )
        (job_dir / "script.json").write_text(
            json.dumps(
                {
                    "topic": spec["topic"],
                    "cta_keyword": spec["cta_keyword"],
                    "total_words": all_words_count,
                    "lines": script_lines,
                    "audit": {"hook_in_line_1": True, "zero_banned_words": True},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (job_dir / "script.txt").write_text(
            "\n".join(x["text"] for x in script_lines) + "\n", encoding="utf-8"
        )
        (job_dir / "assets" / "manifest.json").write_text(
            json.dumps({"assets": manifest_assets}, indent=2), encoding="utf-8"
        )

        # Stage 03 Voice + Stage 05 Music + Stage 06 Scenes + Stage 07 Render + Stage 08 12-check QC
        os.environ["EDGE_TTS_VOICE"] = VOICE_NAME
        run_voice(job_dir, profile_path=profile_path)
        run_music(job_dir)
        run_scenes(job_dir, profile_path=profile_path)

        target_lufs = -14.0
        passed = False
        report_data: Dict[str, Any] = {}
        for loop_idx in range(1, 4):
            run_render(job_dir, target_lufs=target_lufs, music_volume=0.22)
            passed, report_path = run_qc(job_dir, profile_path=profile_path)
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            print(f"[REEL {spec['slug']}] QC loop {loop_idx}/3 -> {report_data['passed_checks']}/{report_data['total_checks']}")
            if passed:
                break
            measured_lufs = float(report_data.get("video_metrics", {}).get("integrated_lufs", -14.0))
            target_lufs = max(-16.0, min(-12.5, target_lufs + (-14.0 - measured_lufs) * 0.8))

        out_mp4 = REELS_DIR / spec["out_name"]
        src_video = job_dir / ("final.mp4" if (job_dir / "final.mp4").exists() else "draft.mp4")
        shutil.copy2(src_video, out_mp4)
        shutil.copy2(job_dir / "thumbnail.jpg", REELS_DIR / (spec["out_name"].replace(".mp4", "_thumb.jpg")))
        shutil.copy2(job_dir / "captions.srt", REELS_DIR / (spec["out_name"].replace(".mp4", ".srt")))
        shutil.copy2(job_dir / "qc-report.json", REELS_DIR / (spec["out_name"].replace(".mp4", "_qc.json")))

        outputs.append(
            {
                "reel": str(out_mp4),
                "qc_passed": passed,
                "qc_score": f"{report_data.get('passed_checks', 0)}/{report_data.get('total_checks', 12)}",
                "metrics": report_data.get("video_metrics", {}),
            }
        )
    return outputs


def write_guide_markdown(walkthrough_mp4: Path, reel_results: List[Dict[str, Any]]) -> Path:
    guide_path = MEDIA_ROOT / "STEP_BY_STEP_GUIDE.md"
    lines = [
        "# HotelRateIntel — Step-by-Step Video Walkthrough, Reels & Hotel Benefits Guide",
        "",
        "## Deliverables Built",
        f"- **Full 1080p Narrated Product Walkthrough (`1920x1080`)**: `{walkthrough_mp4.relative_to(REPO_ROOT)}`",
        f"- **Live Interactive Screen Recordings (`media-pack/screen-recordings/`)**: 6 individual HD MP4 screen captures driving real UI elements",
        f"- **Annotated Step Screenshots (`media-pack/screenshots/`)**: 8 full-HD `1920x1080` step-by-step screenshots",
        "- **9:16 60fps Social Media Video Reels (`media-pack/reels/`)**:",
    ]
    for r in reel_results:
        lines.append(
            f"  - `{Path(r['reel']).name}` — QC `{r['qc_score']}` (`passed={r['qc_passed']}`, {r['metrics'].get('duration_sec')}s @ {r['metrics'].get('fps')}fps, {r['metrics'].get('integrated_lufs')} LUFS)"
        )
    lines.extend(
        [
            "",
            "## How Hotels Use HotelRateIntel Step by Step",
            "1. **Step 1 — Calculate ROI & Leak Exposure (`https://hotelrateintel.com/#top`)**: Enter your hotel room count & ADR into the interactive calculator to measure direct booking upside and payroll freed (`45–68 hrs/mo`, `\$1,125–\$1,700/mo`).",
            "2. **Step 2 — Review Revenue vs. Cost Advantages (`#industry-roi`)**: Inspect how Hotels **Make Money** (plug 18%–44% wholesale OTA leaks on Vio/Agoda/Booking + Art Basel/F1/Boat Show compression ADR lifts) and **Save Money** (`\$0` Free Starter or `\$99/mo` Core vs `\$450–\$900/mo` legacy suites).",
            "3. **Step 3 — Run Live Hotel Website Auditor (`#auditor`)**: Paste your hotel's URL (or pick an illustrative sample) and click **Scan Website & Rates** to detect your booking engine (`SynXis`, `Cloudbeds`, `TravelClick`, `Mews`), inspect the **Channel Rate Ladder SVG** & **Corridor Comp-Set SVG**, and export a printable audit brief.",
            "4. **Step 4 — Open Isolated Hotel Client Portal (`/portal?demo_hotel=1`)**: Each property sees strictly its own BAR, assigned street comp-set, and 6:00 AM **Decision Assistant** verdict (`HOLD`, `RAISE BAR`, or `FIX PARITY`).",
            "5. **Step 5 — Track Pricing Memory Tags & Overnight Courtesy Call Desk (`/portal` Tabs 2 & 3)**: Save private competitor memory notes so afternoon shifts don't panic-discount, and log overnight front-desk occupancy checks cleanly.",
            "6. **Step 6 — Claim Free Account & Scale With AI Dynamic Pro (`#pricing`, `#aidynamic-consultation`, `#blogs`)**: Claim **Tier 1 Free (`\$0/mo`)** forever or upgrade month-to-month (`\$99` Core / `\$199` Pro), and explore custom **AI Dynamic Pro** builds by **Jasmel Acosta & Juan Diaz** including the **`\$99` 48-Hour AI Workflow Audit (`\$2,500+/mo` savings guarantee)**.",
            "",
            "## Installed GitHub MIT Skills Used",
            "- `lackeyjb/playwright-skill` (MIT License) — Playwright browser automation & selector precision",
            "- `testdino-hq/playwright-skill` (MIT License) — Resilient Playwright navigation patterns",
            "- `shreyaskarnik/argo` -> `argo-guide` (MIT License) — Cursor, focus rings, step timing & FFmpeg overlays",
            "- `greentfrapp/testreel` (MIT License) — Step-driven demo video captures",
            "- `noamdorr/saas-product-demo-video` (MIT License) — Real-UI fidelity & frame inspection discipline",
            "- `ThePatriczek/playwright-recast` (MIT License) — Subtitled TTS narration pacing",
        ]
    )
    guide_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return guide_path


def main() -> None:
    ensure_dirs()
    skip_capture = "--skip-capture" in sys.argv
    step_results: List[Dict[str, Any]] = []
    reel_shots: Dict[str, Path] = {}

    if skip_capture and all((CLIPS_DIR / st["clip"]).exists() for st in WALKTHROUGH_STEPS):
        print("[1/4] Reusing existing 8 screenshots & 6 live screen recordings (--skip-capture)...")
        for idx, st in enumerate(WALKTHROUGH_STEPS, 1):
            step_results.append({"index": idx, "raw_mp4": CLIPS_DIR / st["clip"]})
        for key in ("hero", "calc", "roi_matrix", "auditor", "portal_bar", "portal_memory", "portal_calls", "pricing", "consultation"):
            reel_shots[key] = REEL_ASSETS_DIR / f"{key}.png"
    else:
        print("[1/4] Capturing 8 real step screenshots & 6 live Playwright screen recordings...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for idx, st in enumerate(WALKTHROUGH_STEPS, 1):
                    print(f"  Recording {st['clip']} ({st['badge']})...")
                    ctx, page, trim_start = st["action"](browser)
                    out_clip = CLIPS_DIR / st["clip"]
                    finalize_recording(ctx, page, trim_start, out_clip)
                    step_results.append({"index": idx, "raw_mp4": out_clip})

                print("[2/4] Capturing vertical 1000x1040 UI frames for 9:16 Reels...")
                reel_shots = capture_vertical_reel_screenshots(browser)
            finally:
                browser.close()

    print("[3/4] Rendering Full 1920x1080 Narrated Step-by-Step Walkthrough MP4...")
    walkthrough_mp4 = build_full_walkthrough_video(step_results)

    if "--walkthrough-only" in sys.argv:
        print("Skipped Reels re-render (--walkthrough-only); loading existing reel metadata.")
        reel_results = []
        for out_name in (
            "reel_01_step_by_step_how_to_use_1080x1920.mp4",
            "reel_02_hotel_benefits_save_68_hrs_1080x1920.mp4",
        ):
            qc_p = REELS_DIR / out_name.replace(".mp4", "_qc.json")
            rep = json.loads(qc_p.read_text(encoding="utf-8")) if qc_p.exists() else {}
            reel_results.append(
                {
                    "reel": str(REELS_DIR / out_name),
                    "qc_passed": bool(rep.get("overall_passed", False)),
                    "qc_score": f"{rep.get('passed_checks', 0)}/{rep.get('total_checks', 12)}",
                    "metrics": rep.get("video_metrics", {}),
                }
            )
    else:
        print("[4/4] Building & QC-verifying 2 Vertical 1080x1920 60fps Social Reels...")
        reel_results = build_vertical_reels_via_producer(reel_shots)

    guide_md = write_guide_markdown(walkthrough_mp4, reel_results)

    summary = {
        "walkthrough_video": str(walkthrough_mp4),
        "walkthrough_captions": str(VIDEOS_DIR / "walkthrough_captions.srt"),
        "screenshots_count": len(list(SHOTS_DIR.glob("*.png"))),
        "screen_recordings_count": len(list(CLIPS_DIR.glob("*.mp4"))),
        "reels": reel_results,
        "guide_markdown": str(guide_md),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
