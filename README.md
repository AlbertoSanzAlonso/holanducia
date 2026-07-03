# HolanducIA — Real Estate AI Opportunity Finder

Sistema de inteligencia inmobiliaria: scraping, deduplicación, scoring y dashboard de oportunidades.

## Arquitectura de producción

```
┌─────────────────┐         ┌──────────────────────────────────┐
│  Vercel         │  HTTPS  │  VPS (Hetzner + Coolify)         │
│  Frontend React │ ──────► │  FastAPI :9000                   │
│  /api → proxy   │         │  Worker · Postgres · Redis       │
└─────────────────┘         └──────────────────────────────────┘
```

| Componente | Dónde | Notas |
|------------|-------|-------|
| **Frontend** | **Vercel** | `frontend/` — proxy `/api` en `vercel.json` |
| **API** | VPS Docker | Puerto **9000** |
| **Worker** | VPS Docker | Scraping autónomo (Playwright + Crawl4AI) |
| **Postgres** | VPS Docker | pgvector para dedup semántica |
| **Redis** | VPS Docker | Dedup de URLs y hashes raw |

> **InsForge está deprecado.** Todo el backend vive en el VPS. La carpeta `/insforge` es código legacy.

---

## VPS — Backend (Coolify / Docker Compose)

```bash
cp .env.example .env   # editar claves
docker compose up -d --build
docker compose ps
curl http://localhost:9000/health
```

Servicios: `api`, `worker`, `postgres`, `redis`. El servicio `frontend` en compose es **opcional** (solo pruebas locales); en producción el frontend va en Vercel.

### Variables `.env` en el VPS (worker + api)

```env
GROQ_API_KEY=gsk_...
FIRECRAWL_API_KEY=fc-...
OPENAI_API_KEY=sk-...        # embeddings vectoriales (opcional)

# Facebook — login automatizado suele fallar; usar sesión exportada
FB_USER=tu@email.com
FB_PASSWORD=...
FB_SESSION_B64=...           # base64 de fb_session.json (ver abajo)
# FB_SCROLL_STEPS=55         # pasos de scroll por grupo (default 55)
```

Tras cambiar variables en Coolify → **Redeploy** del servicio `worker`.

---

## Vercel — Frontend

1. Importa el repo; **Root Directory**: `frontend`
2. **No uses** `VITE_API_URL=http://IP:9000` en producción (Mixed Content HTTPS→HTTP).
3. El proxy en `frontend/vercel.json` reenvía `/api` y `/health` al VPS por HTTPS.
4. Deja `VITE_API_URL` **vacía** en Vercel (el frontend usa rutas relativas `/api/...`).
5. Build command: `npm run build` · Output: `dist`

Si cambias la IP del VPS, actualiza `vercel.json` y redeploy.

### Desarrollo local del frontend

```bash
cd frontend && npm install && npm run dev
# Proxy Vite → localhost:9000 (ver vite.config.js)
```

---

## Facebook — sesión y scraping

Facebook bloquea logins automatizados. Flujo recomendado:

```bash
# En tu máquina local (terminal externa, no Cursor en Pop!_OS)
python3 -m venv .venv-fb && source .venv-fb/bin/activate
pip install playwright && playwright install chromium
export FB_USER=tu@email.com
export FB_PASSWORD=...
python scrapers/export_fb_session.py
# Copia la línea FB_SESSION_B64=... a Coolify → worker → redeploy
```

El scraper por grupo:
- Hace **55 scrolls** (configurable con `FB_SCROLL_STEPS`)
- Extrae por post: **texto**, **enlace al post** y **fotos** del CDN
- Pipeline: DOM → keywords → Curator → Analyst (Groq) → Persist

Logs útiles: `docker compose logs -f worker` — busca `Scroll paso`, `con enlace`, `con foto`.

---

## Inteligencia y scraping

Pipeline agéntico por anuncio:

```
Raw → Curator (dedup) → Analyst (extracción) → Supervisor (validación IA) → Persist
                                                      ↓
                              Postgres (properties) + pgvector (property_embeddings)
```

| Agente | Rol |
|--------|-----|
| **Curator** | Dedup Redis + BD + similitud vectorial |
| **Analyst** | Groq → JSON estructurado (precio, habitaciones, m²…) |
| **Supervisor** | Valida cada anuncio antes de guardar; rechaza spam/no-inmobiliario |
| **Hunter/Scout** | Descubrimiento en portales y Facebook |

- **Facebook**: Playwright + LangGraph — solo posts con calidad mínima
- **Portales**: Crawl4AI/Firecrawl — URLs reales + fotos
- **Persistencia**: `POST /api/properties` → Postgres + embedding automático en `property_embeddings`
- **Worker**: polling a `/api/scraping-requests/pending`
- **Trigger**: Configuración → "Actualizar ahora"

Requiere `OPENAI_API_KEY` en el servicio **api** (embeddings vectoriales) y `GROQ_API_KEY` en **worker** (Analyst/Supervisor).

---

## Estructura del repo

```
backend/          FastAPI + Postgres + pgvector
scrapers/         Worker, agentes, snipers, export_fb_session.py
frontend/         React (desplegado en Vercel)
docker-compose.yaml
db/               init.sql, migrate_pgvector.sql
skills/holanducia/   Skill del proyecto para agentes IA
insforge/         ⚠️ LEGACY — no usar
```

---

## Documentación para agentes

Skill del proyecto: [`skills/holanducia/SKILL.md`](skills/holanducia/SKILL.md)

Copia local (gitignored): `.claude/skills/holanducia/SKILL.md`
