---
name: holanducia
description: Arquitectura y despliegue de HolanducIA. Usar siempre que trabajes en backend, scrapers, docker, API, frontend Vercel o debugging de producción. NO usar InsForge — está deprecado.
---

# HolanducIA — Stack actual (2026)

## Arquitectura

```
[Vercel]  Frontend React (Vite)
    │  VITE_API_URL → API pública del VPS
    ▼
[VPS Hetzner + Coolify]  docker compose
    ├── api        FastAPI :9000 (público)
    ├── worker     scrapers/main.py
    ├── postgres   pgvector/pgvector:pg16
    └── redis      deduplicación
```

**InsForge NO se usa.** La carpeta `/insforge` es legacy; no crear edge functions ni conectar SDK.

## URLs y variables

| Entorno | Frontend | API | Worker |
|---------|----------|-----|--------|
| Producción | Vercel (`VITE_API_URL`) | `http(s)://IP-o-dominio:9000` | `API_URL=http://api:8000` (red Docker) |
| Local dev | `npm run dev` (proxy Vite) | `localhost:9000` | igual que prod en compose |

### Vercel (obligatorio en Project Settings → Environment Variables)

```
VITE_API_URL=https://tu-dominio-api.com
```

O con IP: `VITE_API_URL=http://123.45.67.89:9000`

**Nunca** `localhost:9000` en Vercel: el navegador del usuario no es el VPS.

### VPS `.env` (Coolify / servidor)

```
GROQ_API_KEY=...
FIRECRAWL_API_KEY=...
OPENAI_API_KEY=...          # embeddings pgvector (opcional)
DATABASE_URL=               # lo setea docker-compose
```

## Despliegue VPS

```bash
git pull
docker compose up -d --build
docker compose ps
curl http://localhost:9000/health
curl http://localhost:9000/api/properties
```

Puerto **9000** expuesto para la API. CORS en FastAPI: `allow_origins=["*"]`.

## Despliegue frontend (Vercel)

- Root directory: `frontend`
- Build: `npm run build`
- Output: `dist`
- Variable: `VITE_API_URL` apuntando a la API del VPS

Tras cambiar `VITE_API_URL`, **redeploy** en Vercel (la variable se bakea en build time).

## Pipeline de scraping

1. Frontend → `POST /api/scraping-requests` (Configuración → Actualizar ahora)
2. Worker → `GET /api/scraping-requests/pending`
3. `DirectorAgent` → Facebook + portales (Hunter, Curator, Analyst)
4. Persist → `POST /api/properties` + embeddings pgvector

## Agentes (`scrapers/agency/`)

| Agente | Rol |
|--------|-----|
| Hunter | Descubre URLs en portales |
| Scout | Extrae posts FB cuando falla DOM |
| Curator | Redis + BD + similitud vectorial |
| Analyst | Groq/OpenAI → JSON estructurado |
| Director | Orquesta misiones |

## Debugging producción

| Síntoma | Causa habitual |
|---------|----------------|
| Frontend vacío en Vercel | `VITE_API_URL` mal o sin redeploy |
| Worker 500 en `/pending` | Tabla `scraping_requests` — reiniciar API |
| Sin embeddings | Falta `OPENAI_API_KEY` en VPS |
| Filtro vacío en UI | Categoría sidebar activa → "Todo el Mercado" |

## Comandos útiles

```bash
docker compose logs -f worker
docker compose logs -f api
curl -X POST "http://localhost:9000/api/properties/embed-backfill?limit=100"
```
