FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Use requirements.txt instead of pyproject.toml so we can install plain
# uvicorn (no [standard] extras), keeping the image buildable on armv7 where
# uvloop is unavailable.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Full source is accessible here because config.yaml lives at the repo root,
# making the entire repo the Docker build context.
COPY aether/ ./aether/

# /data is mapped to persistent storage by the HA supervisor
RUN mkdir -p /data

ENV AETHER_DB_PATH=/data/aether.db \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
