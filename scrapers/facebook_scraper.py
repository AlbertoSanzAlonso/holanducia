import base64
import logging
import os
import re
from pathlib import Path

from playwright.async_api import async_playwright

from scrapers.agency.graphs.facebook_graph import run_facebook_pipeline
from scrapers.fb_image_storage import host_facebook_images
from scrapers.base_scraper import BaseScraper
from scrapers.sync_context import get_mass_fb_scroll_steps, is_mass_mode

logger = logging.getLogger(__name__)

DEBUG_DIR = Path(__file__).parent / "debug"
SESSION_FILE = DEBUG_DIR / "fb_session.json"

EXTRACT_POSTS_JS = """() => {
    const posts = [];
    const seen = new Set();

    function absUrl(href) {
        if (!href) return '';
        try {
            const u = new URL(href, location.href);
            if (!u.hostname.includes('facebook.com')) return '';
            return u.href.split('#')[0];
        } catch (e) {
            return '';
        }
    }

    function postUrlFrom(el) {
        const hrefPatterns = [
            '/posts/', '/permalink/', 'story_fbid', 'multi_permalinks',
            '/photo/', '/videos/', 'fbid=', 'comment_id='
        ];
        for (const a of el.querySelectorAll('a[href]')) {
            const h = (a.getAttribute('href') || '').toLowerCase();
            if (hrefPatterns.some(p => h.includes(p))) {
                const url = absUrl(a.getAttribute('href'));
                if (url) return url;
            }
        }
        for (const a of el.querySelectorAll('a[href*="/groups/"]')) {
            const h = (a.getAttribute('href') || '').toLowerCase();
            if (h.includes('/posts/') || h.includes('permalink') || h.includes('multi_permalinks')) {
                const url = absUrl(a.getAttribute('href'));
                if (url) return url;
            }
        }
        const timeLink = el.querySelector(
            'a[href*="/posts/"], a[href*="permalink"], a[aria-label*="hace"], a[aria-label*="ago"]'
        );
        if (timeLink) return absUrl(timeLink.getAttribute('href'));
        return '';
    }

    function imagesFrom(el) {
        const imgs = [];
        el.querySelectorAll('img').forEach(img => {
            const w = img.naturalWidth || img.width || 0;
            const h = img.naturalHeight || img.height || 0;
            if (w > 0 && w < 100 && h > 0 && h < 100) return;
            let src = '';
            if (img.srcset) {
                const parts = img.srcset.split(',').map(s => s.trim().split(/\s+/)[0]).filter(Boolean);
                src = parts[parts.length - 1] || img.src || '';
            } else {
                src = img.src || img.getAttribute('data-src') || '';
            }
            if (!src) return;
            const lower = src.toLowerCase();
            if (!lower.includes('scontent') && !lower.includes('fbcdn')) return;
            if (lower.includes('emoji') || lower.includes('static.xx') || lower.includes('rsrc.php')) return;
            if (lower.includes('profile') || lower.includes('safe_image')) return;
            imgs.push(src.split('&')[0]);
        });
        el.querySelectorAll('[style*="background-image"]').forEach(el => {
            const m = (el.getAttribute('style') || '').match(/url\\(["']?(https:[^"')]+)/i);
            if (m && (m[1].includes('scontent') || m[1].includes('fbcdn'))) {
                imgs.push(m[1].split('&')[0]);
            }
        });
        return [...new Set(imgs)];
    }

    const articles = document.querySelectorAll('div[role="article"], article');
    articles.forEach(el => {
        const text = (el.innerText || '').trim();
        if (text.length < 40) return;
        const url = postUrlFrom(el);
        const images = imagesFrom(el);
        const key = url || text.slice(0, 150);
        if (seen.has(key)) return;
        seen.add(key);
        posts.push({ text, url, images });
    });

    if (posts.length === 0) {
        const feed = document.querySelector('[role="main"], [role="feed"], #scrollview');
        if (feed) {
            feed.querySelectorAll('div[dir="auto"]').forEach(el => {
                const text = (el.innerText || '').trim();
                if (text.length < 80) return;
                const key = text.slice(0, 150);
                if (seen.has(key)) return;
                seen.add(key);
                posts.push({ text, url: '', images: imagesFrom(el) });
            });
        }
    }

    return posts;
}"""

SCROLL_JS = """(delta) => {
    const step = delta || 900;

    function scrollEl(el, label) {
        el.scrollTop += step;
        return { method: label, scroll: el.scrollTop, max: el.scrollHeight };
    }

    const feedSelectors = [
        '[role="feed"]',
        'div[data-pagelet="GroupFeed"]',
        'div[data-pagelet="StoriesRing"] + div',
    ];
    for (const sel of feedSelectors) {
        const el = document.querySelector(sel);
        if (el && el.scrollHeight > el.clientHeight + 50) {
            return scrollEl(el, sel);
        }
    }

    const main = document.querySelector('[role="main"]');
    if (main) {
        const inner = main.querySelector('[role="feed"]')
            || [...main.querySelectorAll('div')].find(el => {
                const s = getComputedStyle(el);
                return (s.overflowY === 'auto' || s.overflowY === 'scroll')
                    && el.scrollHeight > el.clientHeight + 100;
            });
        if (inner) {
            return scrollEl(inner, 'main>feed');
        }
    }

    const scrollables = [...document.querySelectorAll('div, main')].filter(el => {
        const s = getComputedStyle(el);
        return (s.overflowY === 'auto' || s.overflowY === 'scroll')
            && el.scrollHeight > el.clientHeight + 50;
    });
    const target = scrollables.sort(
        (a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight)
    )[0];
    if (target) {
        return scrollEl(target, 'container');
    }

    window.scrollBy(0, step);
    return {
        method: 'window',
        scroll: window.pageYOffset || document.documentElement.scrollTop || 0,
    };
}"""

FB_SCROLL_STEPS = int(os.getenv("FB_SCROLL_STEPS", "55"))


class FacebookScraper(BaseScraper):
    @staticmethod
    def _scroll_steps() -> int:
        if is_mass_mode():
            return get_mass_fb_scroll_steps()
        return FB_SCROLL_STEPS

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

    def _bootstrap_session_file(self) -> None:
        """Importa sesión Playwright desde env (evita login automatizado bloqueado por FB)."""
        if SESSION_FILE.exists():
            return
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)

        session_b64 = os.getenv("FB_SESSION_B64", "").strip()
        if session_b64:
            try:
                SESSION_FILE.write_bytes(base64.b64decode(session_b64))
                logger.info("Sesión FB importada desde FB_SESSION_B64")
                return
            except Exception as e:
                logger.warning("FB_SESSION_B64 inválido: %s", e)

        session_path = os.getenv("FB_SESSION_PATH", "").strip()
        if session_path and Path(session_path).is_file():
            SESSION_FILE.write_bytes(Path(session_path).read_bytes())
            logger.info("Sesión FB copiada desde %s", session_path)

    async def _persist_lead(self, ai_data: dict, _group_url: str) -> bool:
        return await self.connector.upsert_property(ai_data)

    async def scrape_multiple(self, groups: list):
        self._bootstrap_session_file()
        logger.info(
            "Facebook scraper — FB_USER=%s, FB_PASSWORD=%s, session_file=%s",
            self._mask_email(self.user or ""),
            "set" if self.password else "missing",
            "yes" if SESSION_FILE.exists() else "no",
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
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
                await self._open_discussion_feed(page)

                dom_posts, page_text, scroll_pos = await self._scroll_and_collect(page)
                dom_posts = await self._host_images_for_posts(page, dom_posts)

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
                    rejected = stats.get("rejected_non_real_estate", 0)
                    posts_total = stats.get("posts_total", len(dom_posts))
                    keyword_hits = stats.get("keyword_candidates", 0)
                    if posts_total > 0:
                        hint = (
                            f"{posts_total} posts leídos, {keyword_hits} con keywords, "
                            f"{rejected} descartados por Analyst"
                        )
                    else:
                        hint = diagnosis.get("message") or "sin posts en el DOM"
                    msg = f"Facebook 0 leads en {group_url}: {hint}."
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

        for login_url in (
            "https://www.facebook.com/login",
            "https://m.facebook.com/login.php",
        ):
            if await self._attempt_login_at(page, context, login_url):
                return True

        await self._save_login_debug(page)
        logger.warning(
            "Login Facebook falló en www y m.facebook.com — "
            "Facebook suele bloquear logins automatizados. "
            "Usa FB_SESSION_B64 (cookies exportadas) o verifica la contraseña."
        )
        return False

    async def _attempt_login_at(self, page, context, login_url: str) -> bool:
        try:
            await page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)
            await self._dismiss_cookies(page)

            email_filled = False
            for sel in ('input[name="email"]', 'input#email', 'input[name="username"]', 'input[type="email"]'):
                try:
                    field = page.locator(sel).first
                    if await field.is_visible(timeout=3000):
                        await field.click(timeout=2000)
                        await field.fill(self.user)
                        email_filled = True
                        break
                except Exception:
                    continue

            if not email_filled:
                logger.warning("Login %s: no se encontró campo email", login_url)
                return False

            pass_filled = False
            for sel in ('input[name="pass"]', 'input#pass', 'input[type="password"]'):
                try:
                    field = page.locator(sel).first
                    if await field.is_visible(timeout=3000):
                        await field.click(timeout=2000)
                        await field.fill(self.password)
                        pass_filled = True
                        break
                except Exception:
                    continue

            if not pass_filled:
                logger.warning("Login %s: no se encontró campo password", login_url)
                return False

            clicked = False
            for sel in (
                'button[name="login"]',
                'button[type="submit"]',
                '#loginbutton',
                'button:has-text("Log In")',
                'button:has-text("Iniciar sesión")',
                'div[role="button"]:has-text("Iniciar sesión")',
            ):
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click(timeout=5000)
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                await page.keyboard.press("Enter")

            await page.wait_for_timeout(10000)
            await self._dismiss_cookies(page)

            url = page.url.lower()
            body_snippet = (await page.evaluate("() => document.body.innerText || ''"))[:500].lower()

            if "checkpoint" in url or "two_step" in url or "approvals" in url:
                logger.warning("Facebook checkpoint/2FA en %s", page.url)
                return False
            if "captcha" in body_snippet or "security check" in body_snippet:
                logger.warning("Facebook captcha detectado tras login en %s", login_url)
                return False
            if "login" in url and "logout" not in url:
                logger.warning("Login fallido en %s — URL: %s", login_url, page.url)
                return False

            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(SESSION_FILE))
            logger.info("Login OK via %s — sesión guardada", login_url)
            return True
        except Exception as e:
            logger.warning("Error login en %s: %s", login_url, e)
            return False

    async def _save_login_debug(self, page):
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            path = DEBUG_DIR / "fb_login_failed.png"
            await page.screenshot(path=str(path), full_page=False)
            logger.info("Captura login fallido: %s", path.name)
        except Exception as e:
            logger.warning("No se pudo guardar captura de login: %s", e)

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

    async def _open_discussion_feed(self, page) -> bool:
        """Activa la pestaña Discusión/Publicaciones (FB a veces abre About por defecto)."""
        patterns = [
            r"Discusión",
            r"Discussion",
            r"Publicaciones",
            r"Posts",
        ]
        for pattern in patterns:
            try:
                tab = page.get_by_role("tab", name=re.compile(pattern, re.IGNORECASE))
                if await tab.first.is_visible(timeout=2000):
                    await tab.first.click(timeout=3000)
                    await page.wait_for_timeout(2500)
                    logger.info("Pestaña de feed activada: %s", pattern)
                    return True
            except Exception:
                continue
        for pattern in patterns:
            try:
                link = page.get_by_role("link", name=re.compile(pattern, re.IGNORECASE))
                if await link.first.is_visible(timeout=1500):
                    await link.first.click(timeout=3000)
                    await page.wait_for_timeout(2500)
                    logger.info("Enlace de feed activado: %s", pattern)
                    return True
            except Exception:
                continue
        return False

    async def _scroll_and_collect(self, page):
        posts_by_key: dict[str, dict] = {}
        last_scroll = 0
        stagnant = 0
        last_post_count = 0
        stagnant_posts = 0
        stagnant_post_limit = 8

        for step in range(self._scroll_steps()):
            if page.is_closed():
                break

            try:
                expand_btns = await page.get_by_text(
                    re.compile(r"Ver más|See more", re.IGNORECASE)
                ).all()
                for btn in expand_btns[:8]:
                    if await btn.is_visible():
                        await btn.click(timeout=300)
            except Exception:
                pass

            fragments = await page.evaluate(EXTRACT_POSTS_JS)
            for frag in fragments:
                if not isinstance(frag, dict):
                    text = str(frag).strip()
                    if len(text) < 40:
                        continue
                    key = text[:150]
                    posts_by_key.setdefault(key, {"text": text, "url": "", "images": []})
                    continue

                text = (frag.get("text") or "").strip()
                if len(text) < 40:
                    continue
                url = (frag.get("url") or "").strip()
                images = frag.get("images") or []
                key = url or text[:150]
                existing = posts_by_key.get(key)
                if existing:
                    if url and not existing.get("url"):
                        existing["url"] = url
                    if images and not existing.get("images"):
                        existing["images"] = images
                else:
                    posts_by_key[key] = {"text": text, "url": url, "images": images}

            scroll_delta = 900 if stagnant < 2 else 1400
            scroll_info = await page.evaluate(SCROLL_JS, scroll_delta)
            current_scroll = scroll_info.get("scroll", 0)

            post_count = len(posts_by_key)
            if post_count == last_post_count:
                stagnant_posts += 1
            else:
                stagnant_posts = 0
            last_post_count = post_count

            if step % 5 == 0:
                with_url = sum(1 for p in posts_by_key.values() if p.get("url"))
                with_img = sum(1 for p in posts_by_key.values() if p.get("images"))
                logger.info(
                    "Scroll paso %s/%s: %s posts (%s con enlace, %s con foto), pos=%spx (%s)",
                    step,
                    self._scroll_steps(),
                    post_count,
                    with_url,
                    with_img,
                    current_scroll,
                    scroll_info.get("method", "?"),
                )

            if stagnant_posts >= stagnant_post_limit and post_count <= 5:
                logger.warning(
                    "Feed estancado en %s posts tras %s pasos de scroll — parando temprano",
                    post_count,
                    step + 1,
                )
                break

            if current_scroll == last_scroll:
                stagnant += 1
                if stagnant >= 2:
                    await page.keyboard.press("PageDown")
                if stagnant >= 4:
                    await page.keyboard.press("End")
                    stagnant = 0
            else:
                stagnant = 0

            last_scroll = current_scroll
            await page.wait_for_timeout(1000 if stagnant else 800)

        page_text = await page.evaluate("() => document.body.innerText || ''")
        posts = list(posts_by_key.values())
        if posts and len(posts) <= 5:
            for i, p in enumerate(posts[:3]):
                preview = (p.get("text") or "")[:120].replace("\n", " ")
                logger.info("Post DOM #%s preview: %s…", i + 1, preview)
        return posts, page_text, last_scroll

    async def _host_images_for_posts(self, page, posts: list) -> list:
        for post in posts:
            images = post.get("images") or []
            if not images:
                continue
            key = (post.get("url") or post.get("text", ""))[:120]
            hosted = await host_facebook_images(images, key, page=page)
            if hosted:
                post["images"] = hosted
        return posts

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
