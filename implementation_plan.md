# Implementation Plan - Real Estate AI Opportunity Finder

This project aims to build a high-performance real estate intelligence tool that identifies "Flash Opportunities" by scraping major portals, enriching data with Catastro/AI, and notifying agents in real-time.

## Tech Stack
- **Backend**: InsForge BaaS (PostgreSQL, Auth, Edge Functions, AI)
- **Scrapers**: Playwright / Scrapy (running on Compute or locally)
- **Database**: Managed PostgreSQL (via InsForge)
- **AI/ML**: Built-in InsForge AI (Claude/GPT-4o) + Custom logic
- **Frontend**: Vite + React + Vanilla CSS (Deployed to InsForge Hosting)

## Phase 1: The Radar (MVP - Completed)
- [x] Initialize project structure (`/backend`, `/scrapers`, `/docker`)
- [x] Link to InsForge Project (`HolanducIA`)
- [x] Create `properties` table in the cloud database.
- [x] Implement base Scraper and specialized scrapers.
- [x] Basic Opportunity Scoring and Catastro enrichment.

## Phase 2: Mass Intelligence (Current Focus)
- [x] Integration with **Firecrawl** for anti-bot bypassing.
- [x] Mass Scraping engine for Fotocasa, Habitaclia, and Pisos.com.
- [x] Dynamic field extraction: Parking, Terrace, Pool.
- [ ] Worker auto-triggering on frontend filter changes.

## Next Steps
1. Test the `FirecrawlPortalScraper` with a real query.
2. Refine the extraction schema for better accuracy on specific portals.
3. Optimize the concurrency of the mass scraper to handle hundreds of leads.
