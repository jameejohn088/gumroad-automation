#!/usr/bin/env bash
# Fast tunnel health monitor — checks every 60s, restarts via watchdog.sh on failure.
# Complements the 15-min cron (which handles gist updates + full recovery).
# Run: nohup bash fast-monitor.sh >/tmp/fast-monitor.log 2>&1 &
BACKEND_DIR="$HOME/workspace/gumroad-automation/backend"
while true; do
  sleep 60
  URL="$(cat "$BACKEND_DIR/PUBLIC_URL.txt" 2>/dev/null)"
  if [ -z "$URL" ]; then continue; fi
  CODE="$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL/health" 2>/dev/null)"
  if [ "$CODE" != "200" ]; then
    echo "[$(date '+%F %T')] tunnel unhealthy (code=$CODE), running watchdog..." >> /tmp/fast-monitor.log
    bash "$BACKEND_DIR/watchdog.sh" >> /tmp/fast-monitor.log 2>&1
  fi
done
