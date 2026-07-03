# HolanducIA Frontend

Dashboard React desplegado en **Vercel**. La API vive en el **VPS** (FastAPI puerto 9000).

## Variables de entorno (Vercel)

| Escenario | `VITE_API_URL` |
|-----------|----------------|
| API en VPS solo HTTP (`http://IP:9000`) | **No definir** (vacía). `vercel.json` hace proxy `/api` → VPS. |
| API con HTTPS (`https://api.tu-dominio.com`) | `https://api.tu-dominio.com` |

**No uses** `http://IP:9000` como `VITE_API_URL` en Vercel: el navegador bloquea Mixed Content (HTTPS → HTTP).

Tras cambiar variables o `vercel.json`, **Redeploy**.

## Desarrollo local

```bash
npm install
npm run dev
# http://localhost:5173 — proxy /api → localhost:9000
```

Requiere la API en marcha (`docker compose up -d api` en la raíz del repo).

## Build

```bash
npm run build    # genera dist/
```

Vercel detecta automáticamente Vite si el root directory es `frontend`.

## Notas

- No uses `localhost:9000` como `VITE_API_URL` en Vercel.
- InsForge no se usa; el chat asesor está pendiente de migrar a la API del VPS.
