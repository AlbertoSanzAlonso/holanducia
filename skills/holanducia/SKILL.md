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
    ├── api        FastAPI :9000 (público)
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
GROQ_API_KEY=...
FIRECRAWL_API_KEY=...
OPENAI_API_KEY=...          # embeddings pgvector (opcional)

# Facebook (worker)
FB_USER=...
FB_PASSWORD=...
FB_SESSION_B64=...          # preferido sobre login automatizado
FB_SCROLL_STEPS=55          # opcional, más scroll = más posts por grupo
```

Volumen worker: `fb_session:/app/scrapers/debug` persiste cookies Playwright.

## Despliegue VPS

```bash
git pull
docker compose up -d --build
docker compose ps
curl http://localhost:9000/health
curl http://localhost:9000/api/properties
```

Puerto **9000** expuesto para la API. Tras cambiar env en Coolify → **Redeploy worker**.

## Pipeline de scraping

1. Frontend → `POST /api/scraping-requests` (Configuración → Actualizar ahora)
2. Worker → `GET /api/scraping-requests/pending`
3. `DirectorAgent` → Facebook + portales
4. Persist → `POST /api/properties` + embeddings pgvector

## Facebook (`scrapers/facebook_scraper.py`)

Flujo LangGraph (`facebook_graph.py` → `property_pipeline.py`):

1. Playwright entra al grupo con `FB_SESSION_B64` o login
2. Scroll (`FB_SCROLL_STEPS`, default 55) + expand "Ver más"
3. `EXTRACT_POSTS_JS` → `{text, url, images[]}` por `div[role="article"]`
4. Filtro keywords → Curator (dedup por URL post) → Analyst → Persist

**Sesión FB:** `python scrapers/export_fb_session.py` → copiar `FB_SESSION_B64` a Coolify.

URLs válidas de lead FB: `/posts/`, `/permalink/`, `story_fbid` — ver `portal_utils.is_facebook_post_url()`.

Fotos: CDN `scontent`/`fbcdn` del DOM; Analyst no debe sobrescribirlas con placeholders.

Posts prequalified (keywords FB): si Analyst dice `is_real_estate: false`, el pipeline confía en el filtro previo.

## Portales (Crawl4AI / Firecrawl)

- URLs reales de anuncio vía `portal_utils.extract_listing_urls` + Hunter
- Fotos del listado vía `image_utils` — no inventar URLs `#lead-`
- `resolve_lead_identity()` solo acepta URLs de detalle o post FB

## Agentes (`scrapers/agency/`)

| Agente | Rol |
|--------|-----|
| Hunter | Descubre URLs en portales |
| Scout | Diagnóstico FB + fallback IA si DOM vacío |
| Curator | Redis + BD + similitud vectorial; raw dicts `{text,url,images}` |
| Analyst | Groq/OpenAI → JSON (city, neighborhood, size_m2, bathrooms…) |
| Director | Orquesta misiones |

## Debugging producción

| Síntoma | Causa habitual |
|---------|----------------|
| Frontend vacío en Vercel | Mixed Content — usar proxy `vercel.json`, no `VITE_API_URL` HTTP |
| Worker 500 en `/pending` | Tabla `scraping_requests` — reiniciar API / `startup.py` |
| FB 0 leads, login OK | Pocos posts — subir `FB_SCROLL_STEPS`; revisar keywords/Analyst |
| FB sin foto/enlace | Worker sin redeploy tras cambios en `EXTRACT_POSTS_JS` |
| FB login_required | Regenerar `FB_SESSION_B64` con `export_fb_session.py` |
| Sin embeddings | Falta `OPENAI_API_KEY` en VPS |
| "Ver anuncio" al listado | URL falsa `#lead-` — corregir en Hunter/portal_utils |

## Comandos útiles

```bash
docker compose logs -f worker
docker compose logs -f api
curl -X POST "http://localhost:9000/api/properties/embed-backfill?limit=100"
```
