# Dockerfile para Railway con Python, Chromium y Chromedriver

FROM python:3.10-slim

# Instala Chromium, Chromedriver y dependencias minimas para headless
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget gnupg2 fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    libxrandr2 libxrender1 libxss1 libxtst6 chromium chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# Variables de entorno para Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Railway usa $PORT automaticamente
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 app:app"]
