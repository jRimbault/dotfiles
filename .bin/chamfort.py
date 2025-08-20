#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.13"
# dependencies = ["httpx[http2]", "beautifulsoup4", "lxml"]
# ///
"""
Scrape the price from a Paraboot product page

Heuristic ladder
────────────────
- Visible HTML element whose itemprop/class mentions “price”
- <meta property="product:price:amount" …> or “og:price…”
- JSON-LD  (<script type="application/ld+json">)
- Hidden <input name="gtm_price" value="…">
- Any <script> that contains «"price": "123.45"»
- Last-ditch regex over the whole page text

Every time we fall back we emit a single WARNING via the logging system.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from typing import Callable, Final, Iterable, Optional

import httpx
from bs4 import BeautifulSoup

# ────────── logging ──────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)

# ────────── constants ────────────────────────────────────────────────────────
DEFAULT_URL: Final[str] = (
    "https://www.paraboot.com/homme/bottines/chamfort-galaxy-noire-lisse-noir/"
)
PRICE_RE: Final[re.Pattern[str]] = re.compile(
    r"\d[\d  \u00A0]*[.,]\d{2}(?:\s?€)?",  # thin space & nbsp included
    re.UNICODE,
)


# ────────── CLI entry point ──────────────────────────────────────────────────
async def main(url: str) -> None:
    html = await fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    # ────────── ladder definition & composition ──────────────────────────────────
    heuristics = [
        ("price element", price_from_price_element),
        ("meta", price_from_meta),
        ("JSON‑LD", price_from_jsonld),
        ("<input gtm_price>", price_from_gtm_input),
        ("price inside <script>", price_from_script),
        ("global regex scan", price_from_regex),
    ]

    try:
        price = first(heuristics, soup)
    except LookupError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    # The actual result goes to stdout
    print(f"{price:.2f}€")


# ────────── general helpers ──────────────────────────────────────────────────
async def fetch_html(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, http2=True, timeout=20) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.text


def normalise(price: str) -> float:
    cleaned = price.replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
    return float(cleaned.rstrip("€").replace(",", "."))


# ────────── combinator ───────────────────────────────────────────────────────
def first(
    heuristics: Iterable[tuple[str, Callable[[BeautifulSoup], str | None]]],
    soup: BeautifulSoup,
) -> float:
    """
    Return a function that tries each heuristic in order until one succeeds.
    `heuristics` is an iterable of (label, func) pairs, where *label* names
    the next heuristic (used in the fallback WARNING message).
    """

    heuristics = list(heuristics)

    for idx, (_, func) in enumerate(heuristics):
        if (price := func(soup)) is not None:
            return normalise(price)

        # Log fallback to the *next* heuristic, if any
        if idx < len(heuristics) - 1:
            next_label = heuristics[idx + 1][0]
            logger.warning("Fallback to heuristic %d (%s)", idx + 2, next_label)

    raise LookupError("No price found on the page.")


# ────────── individual heuristics (pure helpers) ─────────────────────────────
def price_from_meta(soup: BeautifulSoup) -> Optional[str]:
    meta = soup.find(
        "meta",
        attrs={
            "content": True,
            "property": [
                "product:price:amount",
                "product:price",
                "og:price:amount",
                "og:price",
            ],
        },
    )
    return meta["content"] if meta else None


def price_from_jsonld(soup: BeautifulSoup) -> Optional[str]:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        def walk(node) -> Optional[str]:
            match node:
                case {"offers": {"price": p}}:
                    return str(p)
                case {"price": p}:
                    return str(p)
                case list() as items:
                    for it in items:
                        if v := walk(it):
                            return v
            return None

        if p := walk(data):
            return p
    return None


def price_from_price_element(soup: BeautifulSoup) -> Optional[str]:
    elem = soup.select_one(
        '[itemprop="price"], [class*="price" i], .woocommerce-Price-amount'
    )
    if elem and (m := PRICE_RE.search(elem.get_text(" ", strip=True))):
        return m.group()
    return None


def price_from_gtm_input(soup: BeautifulSoup) -> Optional[str]:
    if inp := soup.select_one('input[name="gtm_price"][value]'):
        return inp["value"]
    return None


def price_from_script(soup: BeautifulSoup) -> Optional[str]:
    if m := re.search(
        r'"price"\s*:\s*"(\d+(?:[.,]\d{2})?)"', soup.get_text(" ", strip=True)
    ):
        return m.group(1)
    return None


def price_from_regex(soup: BeautifulSoup) -> Optional[str]:
    if m := PRICE_RE.search(soup.get_text(" ", strip=True)):
        return m.group()
    return None


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL))
