# ⚠️ Legacy — InsForge deprecado

Este directorio contiene edge functions y código de cuando el proyecto usaba **InsForge BaaS**.

**Estado actual (2026):**

- Backend: VPS (FastAPI + Postgres + Redis + Worker)
- Frontend: Vercel
- InsForge: **no se usa**

No desplegar ni modificar estas functions salvo migración explícita a FastAPI en `/backend`.

Equivalentes actuales:

| InsForge function | Reemplazo |
|-------------------|-----------|
| `trigger-scrape` | `POST /api/scraping-requests` |
| `monitor-followed` | Worker + Curator |
| `massive-vector-sync` | `POST /api/properties/embed-backfill` |
| `advisor-chat` | Pendiente — endpoint FastAPI |
| `analyze-property` | `OpportunityService` + `AnalystAgent` |
