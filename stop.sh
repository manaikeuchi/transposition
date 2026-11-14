#!/usr/bin/env bash
# Stops anything listening on the backend/frontend ports.
# (npm doesn't forward signals to the vite process it spawns, so we kill by
# port rather than by the pid captured from `npm run dev &`.)
set -uo pipefail
cd "$(dirname "$0")"

for port in 8000 5173; do
  pids=$(lsof -ti ":${port}" -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "$pids" | xargs -r kill
    echo "port ${port} を停止しました。"
  fi
done

rm -f .run/backend.pid .run/frontend.pid
