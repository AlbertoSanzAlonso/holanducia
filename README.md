# Real Estate AI Opportunity Finder

A high-performance system designed to capture, analyze, and notify "Flash Opportunities" in the real estate market.

## 🚀 Production Setup (Hetzner + Coolify)

1.  **Server**: Hetzner CX33 (4 vCPU, 8GB RAM).
2.  **Deployment**: Coolify (Docker Compose Build Pack).
3.  **Port**: API exposed on port `9000`.
4.  **Optimization**: Redis deduplication layer active to save Firecrawl credits.

### Local Development
```bash
cp .env.example .env
docker compose up -d
# API: http://localhost:9000
# Frontend dev:
cd frontend && VITE_API_URL=http://localhost:9000 npm run dev
```

## 🧠 Intelligence Engine
- **Strategy**: Self-hosted stack on VPS (Postgres + Redis + Crawl4AI + Groq).
- **Database**: PostgreSQL in Docker (fresh schema, no InsForge dependency).
- **Deduplication**: Redis-based filtering before extraction.
- **Scoring**: Local opportunity scoring in the FastAPI backend.

## 📁 Structure
- `/backend`: FastAPI service (Port 8080 prod / 8000 local).
- `/scrapers`: Playwright/Firecrawl ingestion layer.
- `docker-compose.yaml`: Unified production config.
- `shared/`: Common schemas and connectors.
