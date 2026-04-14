# Implementation Plan - Real Estate AI Opportunity Finder

This project aims to build a high-performance real estate intelligence tool that identifies "Flash Opportunities" by scraping major portals, enriching data with Catastro/AI, and notifying agents in real-time.

## Tech Stack
- **Backend**: InsForge BaaS (PostgreSQL, Auth, Edge Functions, AI)
- **Scrapers**: Playwright / Scrapy (running on Compute or locally)
- **Database**: Managed PostgreSQL (via InsForge)
- **AI/ML**: Built-in InsForge AI (Claude/GPT-4o) + Custom logic
- **Frontend**: Vite + React + Vanilla CSS (Deployed to InsForge Hosting)

## Phase 1: The Radar (MVP - Current Focus)
### 1. Project Infrastructure
- [x] Initialize project structure (`/backend`, `/scrapers`, `/docker`)
- [x] Link to InsForge Project (`HolanducIA`)
- [x] Create `properties` table in the cloud database.
- [x] Initialize Git and push to [GitHub](git@github.com:AlbertoSanzAlonso/holanducia.git).
- [ ] Create base Pydantic / TypeScript schemas for Property data.

### 2. Ingestion Layer (The "Eyes")
- [ ] Implement a base Scraper class.
- [ ] Create specialized scrapers for **Idealista** and **Milanuncios** (initial 2 sources).
- [ ] Implement a scheduler (APScheduler or Celery) to run every 15-30 mins.

### 3. Intelligence Layer (The "Brain")
- [ ] Property deduplication logic (Address/Coordinates + Catastro logic).
- [ ] Price drop detection (Historical price tracking in TimescaleDB).
- [ ] Basic Opportunity Scoring (v1):
    - Price vs Zone Average.
    - Owner type (Individual vs Agency).
    - Price history trend.

### 4. API & Storage
- [x] InsForge PostgreSQL schema implementation (v1).
- [ ] Edge Functions for data enrichment (Catastro).
- [ ] Frontend Dashboard using InsForge SDK for real-time updates.

## Directory Structure
```text
inmobiliaria_project/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   └── services/
│   └── pyproject.toml
├── scrapers/
│   ├── spiders/
│   ├── base_scraper.py
│   └── main.py
├── docker/
│   └── docker-compose.yml
└── shared/
    └── schemas.py
```

## Next Steps
1. Create the project structure and `docker-compose.yml`.
2. Implement the FastAPI skeleton.
3. Start the first Scraper prototype.
