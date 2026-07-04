"""Fetch de portales con fallback: Crawl4AI (stealth) → Firecrawl → Playwright."""
import logging
import os
from typing import Any, Callable, Dict, Optional

import httpx
from playwright.async_api import async_playwright

from scrapers.image_utils import extract_image_urls, is_portal_index_url
from scrapers.portal_utils import normalize_portal_url

logger = logging.getLogger(__name__)

ANTIBOT_MARKERS = (
    "akamai",
    "anti-bot",
    "pardon our interruption",
    "interruption",
    "imperva",
    "incapsula",
    "captcha",
    "cloudflare",
    "cf-browser-verification",
    "access denied",
    "bot detection",
    "docs.imperva.com",
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

COOKIE_SELECTORS = (
    "#didomi-notice-agree-button",
    "#onetrust-accept-btn-handler",
    "button[id*='accept']",
    ".sui-AtomButton--primary",
)


def is_antibot_content(*, error: str = "", markdown: str = "", html: str = "") -> bool:
    blob = f"{error} {markdown[:3000]} {html[:3000]}".lower()
    return any(marker in blob for marker in ANTIBOT_MARKERS)


def _normalize_page(markdown: str, html: str = "", images: Optional[list] = None) -> Dict[str, Any]:
    return {
        "markdown": markdown or "",
        "html": html or "",
        "images": images or extract_image_urls(html=html, markdown=markdown),
    }


async def fetch_with_firecrawl(url: str) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"url": url, "formats": ["markdown", "html"], "onlyMainContent": True},
            )
            if response.status_code != 200:
                logger.warning("Firecrawl (%s): %s", response.status_code, response.text[:200])
                return None
            payload = response.json().get("data") or {}
            markdown = (payload.get("markdown") or "").strip()
            html = payload.get("html") or ""
            if not markdown and not html:
                return None
            if is_antibot_content(markdown=markdown, html=html):
                logger.warning("Firecrawl sigue bloqueado por WAF: %s", url[:70])
                return None
            logger.info("Firecrawl OK: %s", url[:70])
            return _normalize_page(markdown, html)
    except Exception as e:
        logger.warning("Firecrawl falló en %s: %s", url[:60], e)
        return None


async def fetch_with_playwright(url: str) -> Optional[Dict[str, Any]]:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                user_agent=USER_AGENT,
                locale="es-ES",
                viewport={"width": 1280, "height": 900},
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(2500)

            for selector in COOKIE_SELECTORS:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=1500):
                        await btn.click(timeout=3000)
                        await page.wait_for_timeout(1500)
                        break
                except Exception:
                    continue

            try:
                await page.wait_for_selector('a[href*=".htm"], a[href*="/comprar/"]', timeout=12000)
            except Exception:
                pass

            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollBy(0, 1200)")
            await page.wait_for_timeout(1500)
            html = await page.content()
            markdown = await page.evaluate("() => document.body.innerText || ''")
            await browser.close()

        if is_antibot_content(markdown=markdown, html=html):
            logger.warning("Playwright bloqueado por WAF: %s", url[:70])
            return None
        if len((markdown or "").strip()) < 80:
            logger.warning("Playwright: contenido vacío en %s", url[:70])
            return None
        logger.info("Playwright OK: %s (%s chars)", url[:70], len(markdown))
        return _normalize_page(markdown, html)
    except Exception as e:
        logger.warning("Playwright falló en %s: %s", url[:60], e)
        return None


async def fetch_portal_page(
    url: str,
    *,
    crawl4ai_fetch: Callable[[str], Any],
) -> Optional[Dict[str, Any]]:
    """
    Intenta cargar una página de portal. Si Crawl4AI cae en Akamai/Imperva,
    prueba Firecrawl (solo índices por defecto) y luego Playwright stealth.
    """
    index_only = os.getenv("FIRECRAWL_INDEX_ONLY", "true").lower() == "true"
    allow_firecrawl = (not index_only) or is_portal_index_url(url)

    page = await crawl4ai_fetch(url)
    if page and not is_antibot_content(markdown=page.get("markdown", ""), html=page.get("html", "")):
        return page

    if not allow_firecrawl:
        logger.info(
            "Firecrawl reservado a índices (FIRECRAWL_INDEX_ONLY) — Playwright en ficha: %s",
            url[:70],
        )
        return await fetch_with_playwright(url)

    if page:
        logger.warning("Crawl4AI devolvió página WAF — probando Firecrawl: %s", url[:70])
    else:
        logger.warning("Crawl4AI falló — probando Firecrawl: %s", url[:70])

    page = await fetch_with_firecrawl(url)
    if page:
        return page

    logger.warning("Firecrawl no disponible o bloqueado — probando Playwright: %s", url[:70])
    return await fetch_with_playwright(url)
