import asyncio
import logging
import httpx
import sys
import os

# Ensure shared directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.insforge_connector import InsForgeConnector
from scrapers.agency.director import DirectorAgent

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("HolanducIA_Worker")

async def main():
    # Cargamos desde variables de entorno
    oss_host = os.getenv("INSFORGE_URL")
    api_key = os.getenv("INSFORGE_ANON_KEY")
    
    if not api_key:
        logger.error("❌ Error: INSFORGE_ANON_KEY no encontrada. Revisa tu archivo .env")
        return

    connector = InsForgeConnector(oss_host=oss_host, api_key=api_key)
    director = DirectorAgent()
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    logger.info(f"🏢 HolanducIA Worker iniciado. Conectado a: {oss_host}")
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                # Buscamos una petición pendiente
                url = f"{oss_host}/api/database/records/scraping_requests?status=eq.pending&limit=1"
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    requests = response.json()
                    if requests:
                        request = requests[0]
                        request_id = request['id']
                        logger.info(f"🚀 Misión Recibida: {request_id}")
                        
                        # Marcamos como procesando para que otros workers no la cojan
                        update_url = f"{oss_host}/api/database/records/scraping_requests?id=eq.{request_id}"
                        await client.patch(update_url, json={"status": "processing"}, headers=headers)
                        
                        # Ejecutamos la lógica de rascado masivo
                        # Pasar el request_id si el director lo necesita para contexto
                        await director.execute_mission()
                        
                        # Marcamos como completada
                        await client.patch(update_url, json={
                            "status": "completed", 
                            "processed_at": "now()"
                        }, headers={**headers, "Prefer": "return=minimal"})
                        
                        logger.info(f"🏁 Misión cumplida con éxito: {request_id}")
                    else:
                        # No hay tareas, esperamos un poco
                        pass
                else:
                    logger.error(f"Error de conexión con InsForge: {response.status_code}")
                
            except Exception as e:
                logger.error(f"Error en el bucle del Worker: {e}")
                
            # Esperamos 5 segundos antes de la siguiente comprobación
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Worker detenido por el usuario.")

