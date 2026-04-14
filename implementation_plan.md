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
- [x] Create base Pydantic / TypeScript schemas for Property data.

### 2. Ingestion Layer (The "Eyes")
- [x] Implement a base Scraper class.
- [x] Create specialized scrapers for **Idealista** and **Milanuncios** (initial 2 sources).
- [x] Implement a scheduler (APScheduler) to run every 30 mins.

### 3. Intelligence Layer (The "Brain")
- [x] Property deduplication logic (Database unique constraint implemented).
- [x] Price drop detection (Automated via DB triggers & Price History).
- [x] Basic Opportunity Scoring (v1 implemented in Edge Function).

### 4. API & Storage
- [x] InsForge PostgreSQL schema implementation (v1).
- [x] User Settings table for dynamic configurations.
- [x] Edge Functions for data enrichment (Catastro).
- [x] Frontend Dashboard & Settings View using InsForge SDK.

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
