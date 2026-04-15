import logging
import sys
import os
from typing import Optional

from shared.insforge_connector import InsForgeConnector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Agency.{name}")
        self.connector = InsForgeConnector(
            oss_host=os.getenv("INSFORGE_OSS_HOST", "https://s7pytj95.eu-central.insforge.app"),
            api_key=os.getenv("INSFORGE_API_KEY", "ik_0ed6e333e7a2e51c6c94939d8d8afbcf")
        )
        self.firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
        self.firecrawl_base = "https://api.firecrawl.dev/v1"
        self.knowledge = self.load_knowledge()

    def load_knowledge(self):
        # Go up to agency/ then down to knowledge/
        knowledge_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge", "market_intelligence.md")
        try:
            if os.path.exists(knowledge_path):
                with open(knowledge_path, 'r') as f:
                    return f.read()
            return "No knowledge base found."
        except Exception as e:
            return f"Error loading knowledge: {e}"
