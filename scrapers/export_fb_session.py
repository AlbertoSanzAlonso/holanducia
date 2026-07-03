#!/usr/bin/env python3
"""Genera FB_SESSION_B64 para Coolify tras login manual con Playwright.

Uso:
  export FB_USER=tu@email.com
  export FB_PASSWORD=tu_contraseña   # opcional si logueas a mano
  python scrapers/export_fb_session.py

Copia la salida a Coolify → worker → FB_SESSION_B64 → redeploy.
"""
import asyncio
import base64
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

SESSION_FILE = Path(__file__).parent / "debug" / "fb_session.json"


def _load_dotenv():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


async def main():
    _load_dotenv()
    user = os.getenv("FB_USER")
    password = os.getenv("FB_PASSWORD")

    if not user:
        print("FB_USER no está en .env — puedes loguearte manualmente en el navegador.\n")

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("\n=== Exportar sesión Facebook para HolanducIA ===\n")
    print("1. Se abrirá una ventana de Chrome")
    print("2. Inicia sesión en Facebook (captcha / 2FA si Facebook lo pide)")
    print("3. Cuando veas tu inicio o cualquier página ya logueado, vuelve aquí\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(locale="es-ES")
        page = await context.new_page()
        await page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")

        if password and user:
            try:
                await page.fill('input[name="email"]', user)
                await page.fill('input[name="pass"]', password)
                await page.click('button[name="login"]')
                print("Credenciales enviadas — completa captcha/2FA en el navegador si aparece.\n")
            except Exception:
                print("Rellena login manualmente en el navegador.\n")
        else:
            print("Inicia sesión manualmente en el navegador (email/contraseña/captcha).\n")

        input(">>> Pulsa ENTER aquí cuando hayas iniciado sesión en Facebook... ")

        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        url = page.url.lower()
        if "login" in url or "checkpoint" in url:
            print("\n⚠️  Parece que aún no hay sesión activa:", page.url, file=sys.stderr)
            print("Inicia sesión en el navegador y vuelve a ejecutar el script.", file=sys.stderr)
            await browser.close()
            sys.exit(1)

        await context.storage_state(path=str(SESSION_FILE))
        await browser.close()

    b64 = base64.b64encode(SESSION_FILE.read_bytes()).decode()
    print("\n✅ Sesión guardada en", SESSION_FILE)
    print("\n--- COPIA ESTO EN COOLIFY (worker → FB_SESSION_B64) ---\n")
    print(b64)
    print("\n--- FIN ---")
    print("\nSiguiente: Coolify → worker → añadir variable FB_SESSION_B64 → Redeploy → Actualizar ahora\n")


if __name__ == "__main__":
    asyncio.run(main())
