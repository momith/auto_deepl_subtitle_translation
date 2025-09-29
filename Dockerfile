FROM python:3.12-slim

# Install system dependencies (falls bs4 benötigt wird)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Arbeitsverzeichnis
WORKDIR /app

# Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Dein Skript ins Image kopieren
COPY subtitle_translator.py .

# Standardbefehl
CMD ["python", "-u", "subtitle_translator.py"]

