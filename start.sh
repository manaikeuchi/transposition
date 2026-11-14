#!/usr/bin/env bash
# Starts the backend (FastAPI) and frontend (Vite dev server) for local use.
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p .run

# Audiveris OMR image (only builds if missing)
if ! docker image inspect audiveris-omr:5.11.0 >/dev/null 2>&1; then
  echo "Audiveris の Docker イメージをビルドします(初回のみ、数分かかります)..."
  backend/scripts/build_audiveris_image.sh
fi

if [ ! -d backend/venv ]; then
  echo "backend/venv がありません。先に README の手順でセットアップしてください。"
  exit 1
fi

echo "バックエンドを起動します (http://127.0.0.1:8000)..."
(
  cd backend
  source venv/bin/activate
  nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 > ../.run/backend.log 2>&1 &
  echo $! > ../.run/backend.pid
)

echo "フロントエンドを起動します (http://127.0.0.1:5173)..."
(
  cd frontend
  nohup npm run dev -- --host 127.0.0.1 --port 5173 > ../.run/frontend.log 2>&1 &
  echo $! > ../.run/frontend.pid
)

sleep 2
echo ""
echo "起動しました。ブラウザで http://127.0.0.1:5173 を開いてください。"
echo "停止するには ./stop.sh を実行してください。"
