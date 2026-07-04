import json
import logging
import os
from typing import Any, Dict, Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig, LLMConfig, LLMExtractionStrategy

from scrapers.image_utils import extract_image_urls

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


class Crawl4AIClient:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.llm_provider = os.getenv("CRAWL4AI_LLM_PROVIDER", "openai/gpt-4o-mini")
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            enable_stealth=True,
            user_agent=USER_AGENT,
            viewport_width=1280,
            viewport_height=900,
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

    async def scrape_markdown(self, url: str) -> Optional[str]:
        page = await self.scrape_page(url)
        return page.get("markdown") if page else None

    async def scrape_page(self, url: str) -> Optional[Dict[str, Any]]:
        from scrapers.portal_fetcher import is_antibot_content

        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=10,
            page_timeout=90000,
            magic=True,
            simulate_user=True,
            remove_consent_popups=True,
            delay_before_return_html=2.0,
            wait_until="domcontentloaded",
        )

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            if not result.success:
                logger.warning("Crawl4AI failed for %s: %s", url, result.error_message)
                return None

            markdown = result.markdown or ""
            html = result.cleaned_html or getattr(result, "html", "") or ""
            if is_antibot_content(error=result.error_message or "", markdown=markdown, html=html):
                logger.warning("Crawl4AI página bloqueada (WAF/Akamai): %s", url)
                return None
            media = getattr(result, "media", None) or {}
            media_images = media.get("images") if isinstance(media, dict) else media

            images = extract_image_urls(html=html, markdown=markdown, media_images=media_images)
            return {"markdown": markdown, "html": html, "images": images}

    async def scrape_with_schema(
        self,
        url: str,
        schema: Dict,
        instruction: str = "",
    ) -> Optional[Dict[str, Any]]:
        if not self.openai_key:
            logger.error("OPENAI_API_KEY required for Crawl4AI schema extraction")
            return None

        llm_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(provider=self.llm_provider, api_token=self.openai_key),
            schema=schema,
            extraction_type="schema",
            instruction=instruction or "Extract the requested fields from the page content as JSON.",
            apply_chunking=True,
            chunk_token_threshold=4000,
            input_format="markdown",
        )
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=60000,
            extraction_strategy=llm_strategy,
        )

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            if not result.success:
                logger.warning("Crawl4AI failed for %s: %s", url, result.error_message)
                return None
            if not result.extracted_content:
                return None

            try:
                return json.loads(result.extracted_content)
            except json.JSONDecodeError:
                logger.warning("Crawl4AI returned non-JSON extracted content")
                return None
