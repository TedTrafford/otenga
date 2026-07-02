#!/bin/bash
set -e

# Ensure homebrew node is available
export PATH="/opt/homebrew/bin:$PATH"

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# pandas 2.1.x needs Python 3.9–3.12 (not 3.13+)
pick_python() {
  for cmd in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
      ver=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
      major=${ver%%.*}; minor=${ver#*.}
      if [ "$major" -eq 3 ] && [ "$minor" -ge 9 ] && [ "$minor" -le 12 ]; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  echo "python3"
}

PYTHON=$(pick_python)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ⚡  Otenga BI Platform — Starting..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Backend ──────────────────────────────────
echo ""
echo "📦  Setting up backend..."
cd "$BACKEND"

if [ ! -d ".venv" ]; then
  echo "   Creating virtual environment ($PYTHON)..."
  "$PYTHON" -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt
echo "   ✅  Backend dependencies installed ($("$BACKEND/.venv/bin/python" -V))"

# ── Start backend in background ──────────────
echo ""
echo "🚀  Starting FastAPI backend on :8000..."
"$BACKEND/.venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend health (startup seeds dashboards against remote MySQL — can take ~10s)
echo "   Waiting for API..."
for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "   ✅  Backend ready (${i}s)"
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "   ❌  Backend exited — try: cd backend && .venv/bin/python -m uvicorn app.main:app"
    exit 1
  fi
  sleep 1
  if [ "$i" -eq 60 ]; then
    echo "   ⚠️  Backend still starting (remote DB). Frontend will load; API may follow."
  fi
done

# ── Frontend ─────────────────────────────────
echo ""
echo "📦  Setting up frontend..."
cd "$FRONTEND"

if [ ! -d "node_modules" ]; then
  echo "   Installing npm packages (this may take a moment)..."
  npm install
fi
echo "   ✅  Frontend dependencies installed"

# ── Start frontend ────────────────────────────
echo ""
echo "🌐  Starting React frontend on :5173..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✅  Otenga is running!"
echo ""
echo "   Frontend  →  http://localhost:5173"
echo "   API Docs  →  http://localhost:8000/api/docs"
echo ""
echo " 🔑  Default credentials:"
echo "   admin   / admin123   (superuser)"
echo "   creator / creator123 (creator)"
echo "   viewer  / viewer123  (viewer)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   Press Ctrl+C to stop all services"
echo ""

# Wait & cleanup on exit
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
