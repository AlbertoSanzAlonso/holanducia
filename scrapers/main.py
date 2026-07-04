import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

import httpx
import redis

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agency.director import DirectorAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("HolanducIA_Worker")


async def _is_mission_cancelled(client: httpx.AsyncClient, api_url: str, request_id: int) -> bool:
    try:
        resp = await client.get(f"{api_url}/api/scraping-requests/{request_id}")
        if resp.status_code == 200:
            return resp.json().get("status") == "cancelled"
    except Exception:
        pass
    return False


async def scheduler_loop(client: httpx.AsyncClient, api_url: str) -> None:
    """Programa sync diario automático de todas las fuentes."""
    redis_client = None
    try:
        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0, decode_responses=True
        )
        redis_client.ping()
    except Exception as e:
        logger.warning("Scheduler sin Redis (sync diario manual): %s", e)

    while True:
        try:
            if os.getenv("DAILY_SYNC_ENABLED", "true").lower() != "true":
                await asyncio.sleep(3600)
                continue

            hour = int(os.getenv("DAILY_SYNC_HOUR", "7"))
            now = datetime.now()
            today_key = f"holanducia:daily_sync:{now.strftime('%Y-%m-%d')}"

            if now.hour >= hour and (not redis_client or not redis_client.get(today_key)):
                pending = await client.get(f"{api_url}/api/scraping-requests/pending")
                if pending.status_code == 200 and pending.json():
                    await asyncio.sleep(3600)
                    continue

                settings_resp = await client.get(f"{api_url}/api/settings")
                settings = settings_resp.json() if settings_resp.status_code == 200 else {}
                target = (
                    settings.get("mass_scrape_target")
                    or int(os.getenv("MASS_SCRAPE_TARGET", os.getenv("DAILY_SYNC_TARGET", "500")))
                )
                resp = await client.post(
                    f"{api_url}/api/scraping-requests",
                    json={
                        "source_name": "mass_scrape",
                        "target_leads": target,
                        "status": "pending",
                    },
                )
                if resp.status_code < 400:
                    if redis_client:
                        redis_client.set(today_key, "1", ex=86400)
                    logger.info("Scraping masivo diario encolado — cuota %s", target)
        except Exception as e:
            logger.warning("Error en scheduler diario: %s", e)

        await asyncio.sleep(3600)


async def main():
    api_url = os.getenv("API_URL", "http://api:8000").rstrip("/")
    director = DirectorAgent(api_url=api_url)

    logger.info(
        "HolanducIA Worker iniciado. API: %s | Sync diario: %s a las %s:00",
        api_url,
        os.getenv("DAILY_SYNC_ENABLED", "true"),
        os.getenv("DAILY_SYNC_HOUR", "7"),
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        asyncio.create_task(scheduler_loop(client, api_url))

        while True:
            try:
                response = await client.get(f"{api_url}/api/scraping-requests/pending")
                if response.status_code != 200:
                    logger.error("Error consultando misiones: %s", response.status_code)
                    await asyncio.sleep(5)
                    continue

                request = response.json()
                if not request:
                    await asyncio.sleep(5)
                    continue

                request_id = request["id"]
                logger.info("Mision recibida: %s (%s)", request_id, request.get("source_name"))

                await client.patch(
                    f"{api_url}/api/scraping-requests/{request_id}",
                    json={"status": "processing"},
                )

                total = await director.execute_mission(
                    request=request,
                    cancel_check=lambda: _is_mission_cancelled(client, api_url, request_id),
                )

                await client.patch(
                    f"{api_url}/api/scraping-requests/{request_id}",
                    json={
                        "status": "completed",
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                        "error_message": f"Misión completada — {total} anuncios guardados o actualizados en BD",
                    },
                )
                logger.info("Mision cumplida: %s", request_id)
            except Exception as e:
                logger.error("Error en el bucle del Worker: %s", e)

            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker detenido por el usuario.")
