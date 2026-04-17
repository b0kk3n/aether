#!/bin/bash
set -e

# Read log_level from /data/options.json (written by the HA supervisor from
# the user's add-on config). Falls back to "info" if the file is absent.
LOG_LEVEL=$(python3 -c "
import json
try:
    print(json.load(open('/data/options.json')).get('log_level', 'info'))
except Exception:
    print('info')
")

exec uvicorn \
    aether.api.app:app \
    --host 0.0.0.0 \
    --port 8099 \
    --log-level "${LOG_LEVEL}" \
    --no-access-log
