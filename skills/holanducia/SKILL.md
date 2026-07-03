---
name: holanducia
description: Arquitectura y despliegue de HolanducIA. Usar siempre que trabajes en backend, scrapers, docker, API, frontend Vercel, Facebook scraping o debugging de producción. NO usar InsForge — está deprecado.
---

# HolanducIA — Stack actual (2026)

## Arquitectura

```
[Vercel]  Frontend React (Vite)
    │  /api/* → proxy vercel.json → VPS:9000
    ▼
[VPS Hetzner + Coolify]  docker compose
    ├── api        FastAPI :9000 (público) + embeddings pgvector
    ├── worker     scrapers/main.py (Playwright FB + Crawl4AI portales)
    ├── postgres   pgvector/pgvector:pg16
    └── redis      deduplicación URLs/hashes
```

**InsForge NO se usa.** La carpeta `/insforge` es legacy; no crear edge functions ni conectar SDK.

## URLs y variables

| Entorno | Frontend | API | Worker |
|---------|----------|-----|--------|
| Producción | Vercel (proxy `/api`) | `http(s)://IP:9000` | `API_URL=http://api:8000` (red Docker) |
| Local dev | `npm run dev` (proxy Vite) | `localhost:9000` | igual que prod en compose |

### Vercel

- Root: `frontend`
- **No** poner `VITE_API_URL=http://IP:9000` (Mixed Content). Dejar vacía y usar `frontend/vercel.json`.
- Si cambia la IP del VPS, editar `rewrites` en `vercel.json` y redeploy.

### VPS `.env` (Coolify — worker + api)

```
GROQ_API_KEY=...              # worker: Analyst + Supervisor
OPENAI_API_KEY=...            # api: embeddings pgvector (OBLIGATORIO para vector)
FIRECRAWL_API_KEY=...

# Facebook (worker)
FB_USER=...
FB_PASSWORD=...
FB_SESSION_B64=...          # preferido sobre login automatizado
FB_SCROLL_STEPS=55

# Sync diario (worker)
DAILY_SYNC_ENABLED=true
DAILY_SYNC_HOUR=7
DAILY_SYNC_TARGET=200
```

## Sync diario automático

Worker encola misión `daily_sync` cada día (7:00 por defecto):
- Re-scrapea todas las fuentes (modo sync ignora cache Redis)
- **Crear** URL nueva · **Actualizar** si cambió `content_hash` · **Sin cambios** touch `last_seen_at`
- **Baja** (`is_active=false`) si no visto y cobertura ≥ 25% por fuente
- Siempre Postgres + `property_embeddings` al crear/actualizar

## Pipeline por anuncio

```bash
git pull
docker compose up -d --build
docker compose ps
curl http://localhost:9000/health
curl http://localhost:9000/api/properties
```

Puerto **9000** expuesto para la API. Tras cambiar env en Coolify → **Redeploy worker**.

## Pipeline por anuncio

```
Raw → Curator → Analyst → Supervisor → Persist (Postgres + property_embeddings)
```

1. Frontend → `POST /api/scraping-requests`
2. Worker → `GET /api/scraping-requests/pending`
3. Por cada anuncio: Curator → Analyst → **Supervisor** → Persist
4. API guarda en `properties` + embedding en `property_embeddings`

## Facebook (`scrapers/facebook_scraper.py`)

1. Playwright + `FB_SESSION_B64` + scroll
2. `EXTRACT_POSTS_JS` → `{text, url, images[]}`
3. Filtro `fb_utils` → Curator → Analyst → **Supervisor** → Persist

**Sesión FB:** `python scrapers/export_fb_session.py` → copiar `FB_SESSION_B64` a Coolify.

URLs válidas de lead FB: `/posts/`, `/permalink/`, `story_fbid` — ver `portal_utils.is_facebook_post_url()`.

Fotos: CDN `scontent`/`fbcdn` del DOM.

## Portales (Crawl4AI / Firecrawl)

- URLs reales + fotos → mismo pipeline con **Supervisor**

## Agentes (`scrapers/agency/`)

| Agente | Archivo | Rol |
|--------|---------|-----|
| Hunter | `hunter.py` | URLs en portales |
| Scout | `scout.py` | Diagnóstico FB |
| Curator | `curator.py` | Dedup Redis + BD + vectorial |
| Analyst | `analyst.py` | Extracción JSON |
| **Supervisor** | `supervisor.py` | **Validación IA final por anuncio** |
| Director | `director.py` | Orquestación |

## Debugging producción

| Síntoma | Causa habitual |
|---------|----------------|
| Frontend vacío en Vercel | Mixed Content — usar proxy `vercel.json`, no `VITE_API_URL` HTTP |
| Worker 500 en `/pending` | Tabla `scraping_requests` — reiniciar API / `startup.py` |
| Leads basura guardados | Supervisor rechazando — redeploy worker + api |
| Sin embeddings / similitud | `OPENAI_API_KEY` en servicio **api** |
| "Ver anuncio" al listado | URL falsa `#lead-` — corregir en Hunter/portal_utils |

## Comandos útiles

```bash
docker compose logs -f worker
docker compose logs -f api
curl -X POST "http://localhost:9000/api/properties/embed-backfill?limit=100"
```
