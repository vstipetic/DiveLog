"""
Scrape per-dive gear from Garmin Connect's web UI using Playwright.

Why this exists
---------------
Garmin's dive-gear feature (which suit/mask/fins/etc. you used on each dive) is
served only through the **web** gateway (``connect.garmin.com``), which accepts
only the website's own session token. The ``garminconnect``/garth library logs in
as the **mobile** app and gets a token the web gateway rejects (403), while the
mobile gateway simply has no dive-gear data. So gear is not reachable through the
normal Python API path (see the notes in :mod:`Utilities.GarminConnectClient`).

It *is* rendered on each activity page once you're logged into the website. This
module drives a real logged-in browser (Playwright) to read it. This is inherently
fragile: it depends on Garmin's page markup and login flow, and can break when
they change either.

Design
------
- **Auth**: a *persistent* browser profile (``PROFILE_DIR``). You log into Garmin
  once, in a visible window (handling Cloudflare/MFA yourself); the session is
  saved and reused on later runs. We never handle your Garmin password.
- **Extraction**: a deterministic DOM read of the activity page's gear list. The
  items flagged "active" are the ones used on that dive.
- **Optional LLM step**: the Garmin gear *type* label (e.g. "Exposure Suit",
  "Undergarments") is mapped to a DiveLog gear category. A deterministic map
  handles the known labels; an optional LLM pass classifies anything unknown,
  which keeps it working if Garmin introduces new labels.

Typical use is via the ``scrape_garmin_gear.py`` CLI, not the app.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Persistent browser profile so login survives between runs (git-ignored).
PROFILE_DIR = Path("Storage/.garmin_browser")

_DASHBOARD_URL = "https://connect.garmin.com/modern/"
_ACTIVITY_URL = "https://connect.garmin.com/modern/activity/{activity_id}"

# Deterministic DOM extractor, validated against the live gear list. Returns one
# object per gear item; ``active`` marks the gear used on the current dive.
_EXTRACTOR_JS = r"""
() => {
  const lis = [...document.querySelectorAll('ul[class*="gearList"] > li')];
  return lis.map(li => {
    const icon = li.querySelector('i[class*="icon-diving-gear-"]');
    const iconType = icon ? (icon.className.match(/icon-diving-gear-([a-z]+)/) || [])[1] : null;
    const sub = li.querySelector('[class*="gearSubTitle"]');
    const subText = sub ? sub.textContent.trim() : '';
    const parts = subText.split('•').map(s => s.trim());
    let name = null;
    if (sub && sub.parentElement) {
      const span = sub.parentElement.querySelector('span');
      name = span ? span.textContent.trim() : null;
    }
    return { name, type: parts[0] || null, iconType,
             active: /_active_/.test(li.className),
             total_time: parts[1] || null, dives: parts[2] || null };
  });
}
"""

# Garmin gear type/icon -> DiveLog gear category (UsedGear field name).
# Unmapped types (e.g. Dive Computer, Undergarments) have no DiveLog class today.
_TYPE_TO_CATEGORY = {
    "boots": "boots",
    "fins": "fins",
    "fin": "fins",
    "mask": "mask",
    "gloves": "gloves",
    "glove": "gloves",
    "exposure suit": "suit",
    "exposure": "suit",
    "bcd": "bcd",
}

_VALID_CATEGORIES = {"suit", "mask", "gloves", "boots", "bcd", "fins"}


# A realistic desktop-Chrome user agent (Playwright's default advertises HeadlessChrome).
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _launch_context(p, profile_dir: Path, headless: bool):
    """
    Launch a persistent browser context that avoids Garmin's bot detection.

    Garmin's SSO (Cloudflare) rejects obviously-automated browsers with "an
    unexpected error has occurred". We reduce the automation fingerprint:
    prefer the real installed Chrome, drop the ``--enable-automation`` switch,
    disable the ``AutomationControlled`` blink feature, set a normal user agent,
    and hide ``navigator.webdriver``.
    """
    profile_dir.mkdir(parents=True, exist_ok=True)
    launch_kwargs = dict(
        user_data_dir=str(profile_dir),
        headless=headless,
        args=["--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
        user_agent=_USER_AGENT,
        viewport={"width": 1366, "height": 850},
    )
    try:
        # Use the user's installed Chrome — far less likely to be flagged.
        ctx = p.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
    except Exception:
        # Fall back to Playwright's bundled Chromium if Chrome isn't installed.
        ctx = p.chromium.launch_persistent_context(**launch_kwargs)
    ctx.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    return ctx


def _is_signin_url(url: str) -> bool:
    """True if the URL is a Garmin sign-in / SSO page (i.e. not logged in)."""
    return "signin" in url or "sso.garmin" in url or "/sso/" in url


def category_for(item: Dict[str, Any]) -> Optional[str]:
    """Map a scraped gear item to a DiveLog UsedGear category, or None."""
    for key in (item.get("type"), item.get("iconType")):
        if key:
            cat = _TYPE_TO_CATEGORY.get(str(key).strip().lower())
            if cat:
                return cat
    return None


def parse_total_minutes(total_time: Optional[str]) -> int:
    """Convert a Garmin "HH:MM:SS" gear time string to whole minutes."""
    if not total_time:
        return 0
    bits = [int(b) for b in re.findall(r"\d+", total_time)]
    if len(bits) == 3:
        h, m, _s = bits
        return h * 60 + m
    if len(bits) == 2:
        return bits[0] * 60 + bits[1]
    return bits[0] if bits else 0


def parse_dive_count(dives: Optional[str]) -> int:
    """Extract the integer dive count from a string like "45 Dives"."""
    m = re.search(r"\d+", dives or "")
    return int(m.group()) if m else 0


# ---------------------------------------------------------------------------
# Browser session
# ---------------------------------------------------------------------------

def login(profile_dir: Path = PROFILE_DIR, timeout_seconds: int = 300) -> bool:
    """
    Open a visible browser for a one-time Garmin web login.

    The session is saved into ``profile_dir`` and reused by :func:`scrape_gear`.
    You complete the login (and any Cloudflare/MFA) yourself in the window.

    Returns:
        True once a logged-in dashboard is detected, False on timeout.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = _launch_context(p, profile_dir, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(_DASHBOARD_URL)
        print("A browser window opened. Log into Garmin Connect there "
              "(including any MFA). Waiting up to "
              f"{timeout_seconds}s for you to finish...")

        deadline = time.time() + timeout_seconds
        logged_in = False
        while time.time() < deadline:
            if not _is_signin_url(page.url) and "connect.garmin.com" in page.url:
                # Give the dashboard a moment, then confirm we stayed logged in.
                time.sleep(3)
                if not _is_signin_url(page.url):
                    logged_in = True
                    break
            time.sleep(1)

        if logged_in:
            print("Login detected and saved. You can close this window.")
        else:
            print("Timed out waiting for login.")
        ctx.close()
        return logged_in


def scrape_gear(
    activity_ids: List[str],
    profile_dir: Path = PROFILE_DIR,
    headless: bool = True,
    provider: Any = None,
    per_dive_timeout_ms: int = 15000,
    progress: Optional[Callable[[int, int, str, List[Dict[str, Any]]], None]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scrape the active gear for each activity id.

    Args:
        activity_ids: Garmin activity ids to visit.
        profile_dir: persistent browser profile (must already be logged in; see
            :func:`login`).
        headless: run without a visible window (set False to debug).
        provider: optional ``LLMProvider`` to classify unknown gear types.
        per_dive_timeout_ms: how long to wait for the gear list on each page.
        progress: optional callback ``(done, total, activity_id, items)``.

    Returns:
        ``{activity_id: [gear_item, ...]}`` where each gear item includes an
        added ``category`` key (DiveLog UsedGear field, or None) and only the
        gear actually used on that dive (``active`` was true).

    Raises:
        RuntimeError: if the saved session is not logged in.
    """
    from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

    results: Dict[str, List[Dict[str, Any]]] = {}

    with sync_playwright() as p:
        ctx = _launch_context(p, profile_dir, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        page.goto(_DASHBOARD_URL, wait_until="domcontentloaded")
        if _is_signin_url(page.url):
            ctx.close()
            raise RuntimeError(
                "Garmin session is not logged in. Run GarminGearScraper.login() "
                "(or `scrape_garmin_gear.py --login`) first."
            )

        total = len(activity_ids)
        for i, activity_id in enumerate(activity_ids):
            page.goto(
                _ACTIVITY_URL.format(activity_id=activity_id),
                wait_until="domcontentloaded",
            )
            try:
                page.wait_for_selector(
                    'ul[class*="gearList"] > li', timeout=per_dive_timeout_ms
                )
                raw_items = page.evaluate(_EXTRACTOR_JS)
            except PWTimeout:
                raw_items = []  # dive has no gear list, or it never rendered

            active = [it for it in raw_items if it.get("active")]
            for it in active:
                it["category"] = category_for(it)

            if provider is not None and active:
                _classify_unknown_with_llm(active, provider)

            results[str(activity_id)] = active
            if progress:
                progress(i + 1, total, str(activity_id), active)

        ctx.close()

    return results


def _classify_unknown_with_llm(items: List[Dict[str, Any]], provider: Any) -> None:
    """Fill in ``category`` for items the deterministic map missed, via an LLM.

    Mutates ``items`` in place. Safe: on any failure, categories are left as-is.
    """
    unknown = [it for it in items if not it.get("category")]
    if not unknown:
        return

    import json

    from Utilities.LLMProvider import SystemMessage, UserMessage

    system = (
        "Map each scuba gear item to exactly one DiveLog category from: "
        "suit, mask, gloves, boots, bcd, fins, or other (if it fits none, e.g. "
        "a dive computer or undergarment). Return STRICT JSON: a list of "
        '{"name": <name>, "category": <category>} in the same order as input.'
    )
    payload = [{"name": it.get("name"), "type": it.get("type")} for it in unknown]

    try:
        resp = provider.chat(
            [SystemMessage(system), UserMessage(json.dumps(payload, ensure_ascii=False))]
        )
        text = resp.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        parsed = json.loads(text)
        by_name = {str(d.get("name")): d.get("category") for d in parsed}
        for it in unknown:
            cat = str(by_name.get(str(it.get("name")), "")).lower()
            if cat in _VALID_CATEGORIES:
                it["category"] = cat
    except Exception as exc:  # pragma: no cover - best-effort enrichment
        logger.warning("LLM gear classification failed: %s", exc)


__all__ = [
    "PROFILE_DIR",
    "login",
    "scrape_gear",
    "category_for",
    "parse_total_minutes",
    "parse_dive_count",
]
