# Real Estate AI Opportunity Finder

A high-performance system designed to capture, analyze, and notify "Flash Opportunities" in the real estate market.

## 🚀 Quick Start

### 1. Infrastructure
Ensure you have Docker installed and run:
```bash
cd docker
docker-compose up -d
```

### 2. Backend
Install dependencies and run the API:
```bash
cd backend
pip install -r requirements.txt # Or use your preferred env manager
uvicorn app.main:app --reload
```

### 3. Scrapers
Install Playwright and run a scraper:
```bash
cd scrapers
pip install -r requirements.txt
playwright install chromium
python milanuncios_scraper.py
```

## 🧠 Features (Current Status - Phase 1)
- [x] **Core Backend**: FastAPI architecture initialized.
- [x] **Database**: Ready for TimescaleDB (Time-series for price trends).
- [x] **Intelligence**: Opportunity Scoring logic implemented (Price drops + Market comparison).
- [x] **Ingestion**: Base Playwright scraper structure ready.

## 🛠️ Roadmap
- **Fase 1**: Finish Idealista/Milanuncios scraper logic and DB integration.
- **Fase 2**: Integrate Catastro API for data enrichment.
- **Fase 3**: Implement GPT-4o Vision for photo analysis (e.g., "Reforma necesaria").

## 📁 Structure
- `/backend`: FastAPI service.
- `/scrapers`: Playwright/Scrapy ingestion layer.
- `/docker`: DB/Redis configuration.
- `/shared`: Common schemas for consistency.
