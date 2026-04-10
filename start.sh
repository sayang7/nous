#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Starting Nous..."

# Backend
cd "$ROOT"
if ! python -c "import fastapi" 2>/dev/null; then
  echo "Installing Python dependencies..."
  pip install -r requirements.txt -q
fi

uvicorn api:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "Backend running on http://localhost:8000"

# Frontend
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

npm run dev &
FRONTEND_PID=$!
echo "Frontend running on http://localhost:5173"

echo ""
echo "Nous is ready at http://localhost:5173"
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
