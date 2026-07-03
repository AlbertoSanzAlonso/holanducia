# HolanducIA Frontend

Dashboard React desplegado en **Vercel**. La API vive en el **VPS** (FastAPI puerto 9000).

## Variables de entorno (Vercel)

| Variable | Ejemplo | Obligatorio |
|----------|---------|-------------|
| `VITE_API_URL` | `https://api.holanducia.com` o `http://IP-VPS:9000` | **Sí** |

Configúrala en Vercel → Project → Settings → Environment Variables (Production y Preview).

Después de cambiarla, **Redeploy** el proyecto.

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
