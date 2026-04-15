ARG BUILD_FROM
FROM $BUILD_FROM

# Install system build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    python3-dev

WORKDIR /app

# Install Python dependencies via requirements.txt rather than pyproject.toml.
# This lets us use plain uvicorn (no [standard] extras) so the image builds on
# armv7 (RPi 3), where uvloop — included in uvicorn[standard] — is unavailable.
COPY addon/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application source
COPY aether/ ./aether/

# /data is mapped to persistent storage by the HA supervisor
RUN mkdir -p /data

ENV AETHER_DB_PATH=/data/aether.db \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY addon/run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
