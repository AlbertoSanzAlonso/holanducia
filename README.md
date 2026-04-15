# Real Estate AI Opportunity Finder

A high-performance system designed to capture, analyze, and notify "Flash Opportunities" in the real estate market.

## 🚀 Production Setup (Hetzner + Coolify)

1.  **Server**: Hetzner CX33 (4 vCPU, 8GB RAM).
2.  **Deployment**: Coolify (Docker Compose Build Pack).
3.  **Port**: API exposed on port `8080`.
4.  **Optimization**: Redis deduplication layer active to save Firecrawl credits.

### Local Development
```bash
docker compose up -d
# Run API
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# Run Worker
python scrapers/main.py
```

## 🧠 Intelligence Engine
- **Strategy**: Hybrid approach using InsForge (BaaS) and a private VPS (Scrapers).
- **Deduplication**: Redis-based filtering before Firecrawl extraction.
- **Scoring**: Deep analysis based on price trends and catastro data.

## 📁 Structure
- `/backend`: FastAPI service (Port 8080 prod / 8000 local).
- `/scrapers`: Playwright/Firecrawl ingestion layer.
- `docker-compose.yaml`: Unified production config.
- `shared/`: Common schemas and connectors.
