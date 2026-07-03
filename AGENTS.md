# HolanducIA — Guía para agentes

Lee `skills/holanducia/SKILL.md` antes de tocar backend, scrapers o despliegue.

## Resumen

- **Frontend**: Vercel (`frontend/`) — `VITE_API_URL` → API del VPS
- **Backend**: VPS Docker — FastAPI `:9000`, worker, postgres, redis
- **InsForge**: deprecado (`insforge/LEGACY.md`)

## No hacer

- Usar InsForge SDK, edge functions ni `VITE_INSFORGE_*`
- Poner `localhost:9000` en variables de Vercel
- Asumir que frontend y API están en la misma máquina que el navegador del usuario
