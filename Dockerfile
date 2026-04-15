FROM python:3.11-slim

# Evitar que Python genere archivos .pyc y activar el buffer de salida
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalar solo lo mínimo necesario para que funcione curl y pip
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar y unir los requisitos
COPY backend/pyproject.toml /app/backend/
COPY scrapers/requirements.txt /app/scrapers/

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r scrapers/requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg pydantic-settings redis httpx python-jose[cryptography] passlib[bcrypt]

# Instalar los navegadores de Playwright Y sus dependencias de sistema de forma automática
RUN apt-get update && \
    playwright install chromium && \
    playwright install-deps chromium && \
    rm -rf /var/lib/apt/lists/*

# Copiar el resto del código
COPY . .

# Comando por defecto del API
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
