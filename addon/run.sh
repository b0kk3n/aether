#!/usr/bin/with-contenv bashio

LOG_LEVEL=$(bashio::config 'log_level')
INGRESS_PORT=$(bashio::addon.ingress_port)

bashio::log.info "Starting Aether on port ${INGRESS_PORT}"
bashio::log.info "Log level: ${LOG_LEVEL}"

export AETHER_LOG_LEVEL="${LOG_LEVEL}"
export AETHER_INGRESS_PORT="${INGRESS_PORT}"

exec uvicorn \
    aether.api.app:app \
    --host 0.0.0.0 \
    --port "${INGRESS_PORT}" \
    --log-level "${LOG_LEVEL}" \
    --no-access-log
