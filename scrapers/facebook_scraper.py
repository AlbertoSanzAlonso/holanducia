import logging
import os
import re
from pathlib import Path

from playwright.async_api import async_playwright

from scrapers.agency.graphs.facebook_graph import run_facebook_pipeline
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

DEBUG_DIR = Path(__file__).parent / "debug"
SESSION_FILE = DEBUG_DIR / "fb_session.json"

EXTRACT_POSTS_JS = """() => {
    const posts = [];
    const selectors = [
        'div[role="article"]',
        'article',
        'div[data-ad-preview="message"]',
        'div[data-ad-comet-preview="message"]',
        'div[data-ad-rendering-role="story_message"]',
        'div[data-sigil="m-feed-voice-subtitle"]',
        'div[data-sigil="m-feed-voice-internal"]',
    ];
    selectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            const text = (el.innerText || '').trim();
            if (text.length > 60) posts.push(text);
        });
    });
    const feed = document.querySelector('[role="main"], [role="feed"], #scrollview');
    if (feed) {
        feed.querySelectorAll('div[dir="auto"]').forEach(el => {
            const text = (el.innerText || '').trim();
            if (text.length > 80) posts.push(text);
        });
    }
    return [...new Set(posts)];
}"""

SCROLL_JS = """() => {
    const scrollables = [...document.querySelectorAll('div, main')].filter(el => {
        const s = getComputedStyle(el);
        return (s.overflowY === 'auto' || s.overflowY === 'scroll')
            && el.scrollHeight > el.clientHeight + 50;
    });
    const target = scrollables.sort(
        (a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight)
    )[0];
    if (target) {
        target.scrollTop += 900;
        return { method: 'container', scroll: target.scrollTop };
    }
    window.scrollBy(0, 900);
    return {
        method: 'window',
        scroll: window.pageYOffset || document.documentElement.scrollTop || 0,
    };
}"""


class FacebookScraper(BaseScraper):
    def __init__(self, group_url, limit=50):
        super().__init__("Facebook", base_url="https://facebook.com")
        self.group_url = self._format_url(group_url)
        self.limit = limit
        self.user = os.getenv("FB_USER")
        self.password = os.getenv("FB_PASSWORD")

    @staticmethod
    def _mask_email(email: str) -> str:
        if not email or "@" not in email:
            return "(no configurado)"
        name, domain = email.split("@", 1)
        return f"{name[:3]}***@{domain}"

    def _format_url(self, url):
        if url.isdigit() or not url.startswith("http"):
            return f"https://www.facebook.com/groups/{url}"
        return url.replace("m.facebook.com", "www.facebook.com")

    async def _persist_lead(self, ai_data: dict, _group_url: str) -> bool:
        return await self.connector.upsert_property(ai_data)

    async def scrape_multiple(self, groups: list):
        logger.info(
            "Facebook scraper — FB_USER=%s, FB_PASSWORD=%s",
            self._mask_email(self.user or ""),
            "set" if self.password else "missing",
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            storage_state = str(SESSION_FILE) if SESSION_FILE.exists() else None
            if storage_state:
                logger.info("Restaurando sesión FB desde %s", SESSION_FILE.name)

            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                ),
                locale="es-ES",
                storage_state=storage_state,
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )
            page = await context.new_page()

            if self.user and self.password:
                logged_in = await self._session_is_valid(page) if storage_state else False
                if not logged_in:
                    logged_in = await self._login(page, context)
                if not logged_in:
                    logger.warning(
                        "Login Facebook no confirmado — los grupos pueden seguir en login_required."
                    )
            else:
                logger.warning(
                    "FB_USER/FB_PASSWORD no visibles en el worker — "
                    "revisa env vars en Coolify y redeploy del contenedor worker."
                )

            total_leads = 0
            for group_id in groups:
                if total_leads >= self.limit:
                    break

                group_url = self._format_url(group_id)
                logger.info("Entrando en grupo: %s", group_url)

                await page.goto(group_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                await self._dismiss_cookies(page)

                dom_posts, page_text, scroll_pos = await self._scroll_and_collect(page)

                if not dom_posts:
                    await self._save_debug_artifacts(page, group_id)

                remaining = self.limit - total_leads
                result = await run_facebook_pipeline(
                    group_url=group_url,
                    page_text=page_text,
                    dom_posts=dom_posts,
                    limit=remaining,
                    connector=self.connector,
                    persist_lead=self._persist_lead,
                    is_already_scraped=self.is_already_scraped,
                    mark_as_scraped=self.mark_as_scraped,
                )

                saved = result.get("saved_count", 0)
                method = result.get("extraction_method", "none")
                total_leads += saved

                if result.get("error"):
                    logger.warning("Grupo %s: %s", group_url, result["error"])
                    await self.connector.upsert_scraping_status("processing", f"Facebook: {result['error']}")
                elif saved == 0:
                    stats = result.get("stats") or {}
                    diagnosis = result.get("diagnosis") or {}
                    hint = diagnosis.get("message") or "sin posts extraíbles"
                    rejected = stats.get("rejected_non_real_estate", 0)
                    posts_total = stats.get("posts_total", 0)
                    msg = (
                        f"Facebook 0 leads en {group_url}: {hint}. "
                        f"posts={posts_total}, descartados_ia={rejected}. "
                        "¿FB_USER/FB_PASSWORD configurados?"
                    )
                    logger.warning(msg)
                    await self.connector.upsert_scraping_status("processing", msg)
                else:
                    logger.info(
                        "Grupo %s: %s leads (método=%s, scroll=%spx)",
                        group_url,
                        saved,
                        method,
                        scroll_pos,
                    )

            await browser.close()
            logger.info("Scraper finalizado. Total inyectado: %s", total_leads)
            return total_leads

    async def _session_is_valid(self, page) -> bool:
        try:
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2500)
            await self._dismiss_cookies(page)
            url = page.url.lower()
            if any(token in url for token in ("login", "checkpoint", "two_step")):
                return False
            logger.info("Sesión Facebook activa (cookies previas).")
            return True
        except Exception as e:
            logger.warning("No se pudo validar sesión FB: %s", e)
            return False

    async def _login(self, page, context) -> bool:
        logger.info("Fase login: identificando a %s...", self._mask_email(self.user or ""))
        try:
            await page.goto("https://www.facebook.com/login", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(1500)
            await self._dismiss_cookies(page)
            await page.wait_for_selector('input[name="email"]', timeout=15000)
            await page.fill('input[name="email"]', self.user)
            await page.fill('input[name="pass"]', self.password)

            for sel in ['button[name="login"]', 'button:has-text("Log In")', 'button:has-text("Iniciar sesión")']:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click(timeout=5000)
                        break
                except Exception:
                    continue

            await page.wait_for_timeout(8000)
            await self._dismiss_cookies(page)

            url = page.url.lower()
            if "checkpoint" in url or "two_step" in url:
                logger.warning(
                    "Facebook pide verificación extra (checkpoint/2FA): %s — "
                    "inicia sesión manualmente una vez o desactiva 2FA para esta cuenta bot.",
                    page.url,
                )
                return False
            if "login" in url:
                logger.warning("Login fallido — sigue en página de login: %s", page.url)
                return False

            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(SESSION_FILE))
            logger.info("Login OK — sesión guardada en %s", SESSION_FILE.name)
            return True
        except Exception as e:
            logger.warning("Error en login: %s", e)
            return False

    async def _dismiss_cookies(self, page):
        patterns = [
            r"Allow all cookies",
            r"Permitir todas las cookies",
            r"Accept All",
            r"Aceptar todo",
            r"Allow essential and optional cookies",
        ]
        for pattern in patterns:
            try:
                btn = page.get_by_role("button", name=re.compile(pattern, re.IGNORECASE))
                if await btn.first.is_visible(timeout=1500):
                    await btn.first.click(timeout=3000)
                    await page.wait_for_timeout(1000)
                    return
            except Exception:
                continue

    async def _scroll_and_collect(self, page):
        unique_posts = set()
        last_scroll = 0
        stagnant = 0

        for step in range(35):
            if page.is_closed():
                break

            try:
                expand_btns = await page.get_by_text(
                    re.compile(r"Ver más|See more", re.IGNORECASE)
                ).all()
                for btn in expand_btns[:5]:
                    if await btn.is_visible():
                        await btn.click(timeout=300)
            except Exception:
                pass

            fragments = await page.evaluate(EXTRACT_POSTS_JS)
            for frag in fragments:
                if len(frag.strip()) > 50:
                    unique_posts.add(frag.strip())

            scroll_info = await page.evaluate(SCROLL_JS)
            current_scroll = scroll_info.get("scroll", 0)

            if step % 5 == 0:
                logger.info(
                    "Scroll paso %s: %s fragmentos, pos=%spx (%s)",
                    step,
                    len(unique_posts),
                    current_scroll,
                    scroll_info.get("method", "?"),
                )

            if current_scroll == last_scroll:
                stagnant += 1
                if stagnant >= 3:
                    await page.keyboard.press("PageDown")
                    stagnant = 0
            else:
                stagnant = 0

            last_scroll = current_scroll
            await page.wait_for_timeout(1200)

        page_text = await page.evaluate("() => document.body.innerText || ''")
        return list(unique_posts), page_text, last_scroll

    async def _save_debug_artifacts(self, page, group_id):
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^\w-]", "_", str(group_id))[:40]
        screenshot_path = DEBUG_DIR / f"fb_{safe_id}.png"
        html_path = DEBUG_DIR / f"fb_{safe_id}.html"

        try:
            await page.screenshot(path=str(screenshot_path), full_page=False)
            html = await page.content()
            html_path.write_text(html[:50000], encoding="utf-8")
            logger.info("Debug guardado: %s, %s", screenshot_path.name, html_path.name)
        except Exception as e:
            logger.warning("No se pudo guardar debug: %s", e)

    async def scrape(self):
        return await self.scrape_multiple([self.group_url])
