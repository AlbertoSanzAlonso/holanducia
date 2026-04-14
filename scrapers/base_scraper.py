import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional
from playwright.async_api import async_playwright, Page
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import sys
import os

# Ensure shared directory is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.insforge_connector import InsForgeConnector

class BaseScraper(ABC):
    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.results = []
        
        # Load InsForge config (Hardcoded for this phase, should use env in prod)
        self.connector = InsForgeConnector(
            oss_host="https://s7pytj95.eu-central.insforge.app",
            api_key="ik_0ed6e333e7a2e51c6c94939d8d8afbcf"
        )

    @abstractmethod
    async def scrape(self):
        """Main scraping logic to be implemented by subclasses"""
        pass

    async def get_page_content(self, url: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Subtle delay or random movements could be added here to avoid detection
            logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until="networkidle")
            
            content = await page.content()
            await browser.close()
            return content

    async def save_results(self):
        logger.info(f"Saving {len(self.results)} results from {self.source_name} to InsForge")
        for prop in self.results:
            try:
                # 1. Logic for Market Average (Mocked for now)
                market_avg = 250000.0 
                
                # 2. Analyze via Edge Function
                analysis = await self.connector.analyze_property(prop, market_avg)
                
                # 3. Enrich data
                prop['opportunity_score'] = analysis['score']
                prop['opportunity_reasons'] = analysis['reasons']
                
                # 4. Save to DB
                await self.connector.upsert_property(prop)
                logger.info(f"Saved property: {prop['url']} | Score: {prop['opportunity_score']}")
            except Exception as e:
                logger.error(f"Error saving property {prop.get('url')}: {e}")
