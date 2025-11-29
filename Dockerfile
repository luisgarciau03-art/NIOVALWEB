<<<<<<< HEAD
# Dockerfile para Render con Python, Chromium y Chromedriver
FROM python:3.10-slim

# Instala Chromium y Chromedriver usando los paquetes correctos
RUN apt-get update && \
    apt-get install -y wget gnupg2 && \
    echo "deb http://deb.debian.org/debian bullseye main" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y chromium chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# Variables de entorno para Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Comando para iniciar tu app (ajusta si usas Flask, FastAPI, etc)
CMD ["python", "app.py"]
=======
# Dockerfile para Render con Python, Chromium y Chromedriver
FROM python:3.10-slim

# Instala Chromium y Chromedriver usando los paquetes correctos
RUN apt-get update && \
    apt-get install -y wget gnupg2 && \
    echo "deb http://deb.debian.org/debian bullseye main" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y chromium chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# Variables de entorno para Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Comando para iniciar tu app (ajusta si usas Flask, FastAPI, etc)
CMD ["python", "app.py"]
>>>>>>> 0737b5f4972923487d8dc6b802ec9c2d1b72da37
