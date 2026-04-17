FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (plain uvicorn — no [standard] extras so the
# image builds on armv7 where uvloop is unavailable).
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install the aether package from source. pip copies the static files into
# site-packages via the package-data declaration in pyproject.toml, giving
# Path(__file__) a stable, predictable location regardless of WORKDIR.
COPY aether/ ./aether/
COPY pyproject.toml ./
RUN pip install --no-cache-dir --no-deps .

# /data is mapped to persistent storage by the HA supervisor
RUN mkdir -p /data

ENV AETHER_DB_PATH=/data/aether.db \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
