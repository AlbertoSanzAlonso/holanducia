FROM python:3.11-slim

# Evitar que Python genere archivos .pyc y activar el buffer de salida para logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalar dependencias del sistema necesarias para Playwright
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    librandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar y unir los requisitos
COPY backend/pyproject.toml /app/backend/
COPY scrapers/requirements.txt /app/scrapers/

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r scrapers/requirements.txt
# Instalamos también las del backend (usando pip sobre pyproject.toml es posible con librerías modernas)
RUN pip install --no-cache-dir fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg pydantic-settings redis httpx python-jose[cryptography] passlib[bcrypt]

# Instalar los navegadores de Playwright (solo Chromium para ahorrar espacio)
RUN playwright install chromium
RUN playwright install-deps chromium

# Copiar el resto del código
COPY . .

# Por defecto usaremos el comando de la API, pero en el compose lo sobreescribiremos para el worker
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
