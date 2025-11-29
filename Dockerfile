# Dockerfile para Render con Python, Chromium y Chromedriver
FROM python:3.10-slim

# Instala dependencias de sistema
RUN apt-get update && \
    apt-get install -y chromium-driver chromium-browser && \
    rm -rf /var/lib/apt/lists/*

# Establece variables de entorno para Selenium
ENV CHROME_BIN=/usr/bin/chromium-browser
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Copia el código fuente
WORKDIR /app
COPY . /app

# Instala dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando para iniciar tu app (ajusta si usas Flask, FastAPI, etc)
CMD ["python", "app.py"]
