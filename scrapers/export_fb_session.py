#!/usr/bin/env python3
"""Genera FB_SESSION_B64 para Coolify tras login manual con Playwright.

Uso local (con FB_USER/FB_PASSWORD en .env):
  python scrapers/export_fb_session.py

Copia la salida a Coolify → worker → FB_SESSION_B64 → redeploy.
"""
import asyncio
import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright

SESSION_FILE = Path(__file__).parent / "debug" / "fb_session.json"


async def main():
    user = os.getenv("FB_USER")
    password = os.getenv("FB_PASSWORD")
    if not user or not password:
        print("Define FB_USER y FB_PASSWORD en el entorno.", file=sys.stderr)
        sys.exit(1)

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(locale="es-ES")
        page = await context.new_page()
        await page.goto("https://www.facebook.com/login")
        print("Si hace falta, completa login/captcha/2FA en la ventana del navegador...")
        await page.fill('input[name="email"]', user)
        await page.fill('input[name="pass"]', password)
        await page.click('button[name="login"]')
        await page.wait_for_timeout(15000)
        input("Cuando veas el feed de Facebook, pulsa Enter aquí...")
        await context.storage_state(path=str(SESSION_FILE))
        await browser.close()

    b64 = base64.b64encode(SESSION_FILE.read_bytes()).decode()
    print("\n--- FB_SESSION_B64 (pegar en Coolify worker) ---\n")
    print(b64)


if __name__ == "__main__":
    asyncio.run(main())
