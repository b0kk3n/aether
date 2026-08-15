FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies (plain uvicorn — no [standard] extras so the image
# builds on armv7 where uvloop is unavailable).
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy the pantry package source
COPY pantry/ ./pantry/

# /data is mapped to persistent storage by the HA supervisor
RUN mkdir -p /data

ENV AETHER_PANTRY_DB_PATH=/data/pantry.db \
    PANTRY_STATIC_DIR=/app/pantry/web/static \
    PANTRY_TEMPLATE_DIR=/app/pantry/web/templates \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
