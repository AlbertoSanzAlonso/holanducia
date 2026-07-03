# Implementation Plan — HolanducIA

## Tech Stack (actual)

- **Frontend**: Vite + React + Tailwind → **Vercel**
- **Backend**: FastAPI → **VPS** (Docker, puerto 9000)
- **Database**: PostgreSQL 16 + **pgvector** (Docker)
- **Cache / Dedup**: Redis (Docker)
- **Scrapers**: Playwright, Crawl4AI, Firecrawl (worker Docker)
- **AI**: Groq (Analyst), OpenAI embeddings (vectorial, opcional)

~~InsForge~~ — **deprecado**. No usar BaaS ni edge functions.

## Phase 1: The Radar (Completed)

- [x] Estructura `/backend`, `/scrapers`, `/frontend`
- [x] PostgreSQL self-hosted + FastAPI CRUD
- [x] Scrapers Facebook + portales
- [x] Scoring de oportunidades en backend

## Phase 2: Production VPS (Completed)

- [x] Hetzner CX33 + Coolify + Docker Compose
- [x] Worker con polling de `scraping_requests`
- [x] Redis deduplication (ahorro Firecrawl)
- [x] pgvector + Curator semántico

## Phase 3: Frontend Vercel (Completed)

- [x] Frontend desacoplado en Vercel
- [x] `VITE_API_URL` → API del VPS
- [x] InsForge eliminado del flujo de producción

## Phase 4: Marco agéntico (En curso)

- [x] Hunter + Curator + Analyst + Director
- [x] LangGraph pipeline (Facebook + portales)
- [x] Embeddings pgvector
- [ ] Chat asesor vía API VPS (sustituir InsForge functions)
- [ ] Vision analysis (fotos)
- [ ] Catastro deep-link automatizado
