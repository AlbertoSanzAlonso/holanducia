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

## Phase 2: Mass Intelligence & Production (Completed)
- [x] Integration with **Firecrawl** for anti-bot bypassing.
- [x] Mass Scraping engine for Fotocasa, Habitaclia, and Pisos.com.
- [x] **Deduplication Strategy** using Redis to save Firecrawl credits.
- [x] **Production Deployment**: Hetzner CX33 (8GB) + Coolify + Docker.
- [x] Worker auto-triggering on pending requests.

## Phase 3: AI & Enrichment (Current Focus)
1.  **Vision analysis**: Implement GPT-4o Vision for photo analysis (e.g., "Reforma necesaria", "Luminoso").
2.  **Catastro deep-link**: Automated surface and year-built validation.
3.  **Refine extraction**: Improve sub-unit logic (parking, storage room) for all portals.
