import httpx
import os
from typing import Dict, Any

class InsForgeConnector:
    def __init__(self, oss_host: str, api_key: str):
        self.oss_host = oss_host.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def upsert_property(self, property_data: Dict[str, Any]):
        """Upserts a property to the cloud database"""
        # Specify on_conflict to handle deduplication correctly
        url = f"{self.oss_host}/api/database/records/properties?on_conflict=url"
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=property_data, headers=headers)
            response.raise_for_status()
            return response.json()

    async def analyze_property(self, property_data: Dict[str, Any], market_avg: float):
        """Calls the edge function to get opportunity analysis"""
        url = f"{self.oss_host}/functions/analyze-property"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                json={"property": property_data, "market_avg": market_avg},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    async def get_settings(self):
        """Fetches the latest user settings from the database"""
        url = f"{self.oss_host}/api/database/records/user_settings?select=*&limit=1"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None
