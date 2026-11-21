#!/bin/bash
set -euo pipefail

units=(app-m appmeteo hanzhub-{calendar,coinlist,dashboard2,henk-studio,iot,lora-web,predicapp,radio,stream-web,whiteboard})
for unit in "${units[@]}"; do
    systemctl is-active --quiet "$unit"
    systemctl is-enabled --quiet "$unit"
    printf '%s active, enabled\n' "$unit"
done

for path in 4001/ 4001/living-glass/ 4002/ 4002/assets/henk-idle.webp \
    4011/api/iot/health 4011/api/iot/devices 4012/api/calendar/status \
    4014/health 4014/api/v1/presets 5000/api/current 5000/api/history \
    5001/ 8084/api/system_health 8085/version 8086/health 8088/status \
    8099/api/events/count; do
    curl --fail --silent --show-error --max-time 20 --output /dev/null \
        --write-out "%{http_code} $path\n" "http://127.0.0.1:$path"
done

# The local validation certificate is self-signed.
curl --insecure --fail --silent --show-error --max-time 20 --output /dev/null \
    --write-out '%{http_code} 4013/api/calendar/status (TLS)\n' \
    https://127.0.0.1:4013/api/calendar/status
