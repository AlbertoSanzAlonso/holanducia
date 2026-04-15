import httpx
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class InsForgeConnector:
    def __init__(self, oss_host: str, api_key: str):
        self.oss_host = oss_host.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def upsert_property(self, property_data: Dict[str, Any]):
        """Upserts a property to the cloud database with robust error logging"""
        url = f"{self.oss_host}/api/database/records/properties?on_conflict=url"
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=property_data, headers=headers)
                if response.status_code >= 400:
                    logger.error(f"DB Insert Error {response.status_code}: {response.text}")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to upsert property {property_data.get('url')}: {e}")
                raise e

    async def analyze_property(self, property_data: Dict[str, Any], market_avg: float):
        """Calls the edge function to get opportunity analysis"""
        url = f"{self.oss_host}/functions/v1/analyze-property" 
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json={"property": property_data, "market_avg": market_avg},
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Analysis edge function failed: {e}")
                return {"score": 0, "reasons": ["Error en análisis automático"]}

    async def enrich_catastro(self, address: str, city: str):
        """Calls the Catastro enrichment edge function"""
        url = f"{self.oss_host}/functions/v1/enrich-catastro"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json={"address": address, "city": city},
                    headers=self.headers
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception as e:
                logger.warning(f"Catastro enrichment failed: {e}")
                return None

    async def get_settings(self):
        """Fetches the latest user settings from the database"""
        url = f"{self.oss_host}/api/database/records/user_settings?select=*&limit=1"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                return data[0] if data else None
            except Exception as e:
                logger.error(f"Failed to fetch settings: {e}")
                return None

    async def check_property_exists(self, url: str) -> bool:
        """Checks if a property with the given URL already exists in the DB"""
        check_url = f"{self.oss_host}/api/database/records/properties?url=eq.{url}&select=id"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(check_url, headers=self.headers)
                return len(response.json()) > 0
            except:
                return False

    async def upsert_scraping_status(self, status: str, message: str):
        """Updates the latest scraping request with a specific status and message"""
        # 1. Obtener la ID de la última misión
        url = f"{self.oss_host}/api/database/records/scraping_requests?select=id&order=requested_at.desc&limit=1"
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, headers=self.headers)
                if res.status_code == 200 and res.json():
                    last_id = res.json()[0]['id']
                    # 2. Actualizarla con el estado de error/bloqueo
                    up_url = f"{self.oss_host}/api/database/records/scraping_requests?id=eq.{last_id}"
                    await client.patch(up_url, json={"status": status, "error_message": message}, headers=self.headers)
                    logger.info(f"🚨 Status reported to DB: {status}")
            except Exception as e:
                logger.error(f"Failed to report scraping status: {e}")
