# HolanducIA — Real Estate AI Opportunity Finder

Sistema de inteligencia inmobiliaria: scraping, deduplicación, scoring y dashboard de oportunidades.

## Arquitectura de producción

```
┌─────────────────┐         ┌──────────────────────────────────┐
│  Vercel         │  HTTPS  │  VPS (Hetzner + Coolify)         │
│  Frontend React │ ──────► │  FastAPI :9000                   │
│  VITE_API_URL   │         │  Worker · Postgres · Redis       │
└─────────────────┘         └──────────────────────────────────┘
```

| Componente | Dónde | Notas |
|------------|-------|-------|
| **Frontend** | **Vercel** | `frontend/` — variable `VITE_API_URL` |
| **API** | VPS Docker | Puerto **9000** |
| **Worker** | VPS Docker | Scraping autónomo |
| **Postgres** | VPS Docker | pgvector para dedup semántica |
| **Redis** | VPS Docker | Dedup de URLs |

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

### Variables `.env` en el VPS

```env
GROQ_API_KEY=gsk_...
FIRECRAWL_API_KEY=fc-...
OPENAI_API_KEY=sk-...        # embeddings vectoriales (opcional)
```

---

## Vercel — Frontend

1. Importa el repo; **Root Directory**: `frontend`
2. **Environment Variable** (Production + Preview):

   ```
   VITE_API_URL=https://api.tu-dominio.com
   ```

   Usa la URL pública de tu API en el VPS (IP:9000 o dominio con reverse proxy).

3. Build command: `npm run build` · Output: `dist`

4. Tras cambiar `VITE_API_URL`, haz **Redeploy** (se incluye en el build).

### Desarrollo local del frontend

```bash
cd frontend && npm install && npm run dev
# Proxy Vite → localhost:9000 (ver vite.config.js)
```

---

## Inteligencia y scraping

- **Scrapers**: Facebook (LangGraph), portales via Crawl4AI/Firecrawl
- **Agentes**: Hunter → Curator (Redis + BD + pgvector) → Analyst (Groq) → Persist
- **Worker**: polling a `/api/scraping-requests/pending`
- **Trigger manual**: Frontend → Configuración → "Actualizar ahora"

---

## Estructura del repo

```
backend/          FastAPI + Postgres + pgvector
scrapers/         Worker, agentes, snipers
frontend/         React (desplegado en Vercel)
docker-compose.yaml
db/               init.sql, migrate_pgvector.sql
insforge/         ⚠️ LEGACY — no usar
```

---

## Documentación para agentes

Skill del proyecto: `.claude/skills/holanducia/SKILL.md`
