import json
import logging
import os
from typing import Any, Dict, Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig, LLMConfig, LLMExtractionStrategy

logger = logging.getLogger(__name__)


class Crawl4AIClient:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.llm_provider = os.getenv("CRAWL4AI_LLM_PROVIDER", "openai/gpt-4o-mini")
        self.browser_config = BrowserConfig(headless=True, verbose=False)

    async def scrape_markdown(self, url: str) -> Optional[str]:
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=10,
            page_timeout=60000,
        )

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            if not result.success:
                logger.warning("Crawl4AI failed for %s: %s", url, result.error_message)
                return None
            return result.markdown or result.cleaned_html

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
