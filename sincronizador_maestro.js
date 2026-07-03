# ⚠️ Legacy — usar API del VPS (POST /api/properties). Ver insforge/LEGACY.md

const API_URL = process.env.API_URL || "http://localhost:9000";

async function sync() {
  console.log("Usar docker compose worker + API FastAPI en el VPS.");
  console.log("API:", API_URL);
}

sync();
