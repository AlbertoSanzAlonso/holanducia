import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

import httpx

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agency.director import DirectorAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("HolanducIA_Worker")


async def main():
    api_url = os.getenv("API_URL", "http://api:8000").rstrip("/")
    director = DirectorAgent(api_url=api_url)

    logger.info("HolanducIA Worker iniciado. API: %s", api_url)

    async with httpx.AsyncClient(timeout=60.0) as client:
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
                logger.info("Mision recibida: %s", request_id)

                await client.patch(
                    f"{api_url}/api/scraping-requests/{request_id}",
                    json={"status": "processing"},
                )

                await director.execute_mission(request=request)

                await client.patch(
                    f"{api_url}/api/scraping-requests/{request_id}",
                    json={
                        "status": "completed",
                        "processed_at": datetime.now(timezone.utc).isoformat(),
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
