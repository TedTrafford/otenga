#!/bin/bash
set -e

# Ensure homebrew node is available
export PATH="/opt/homebrew/bin:$PATH"

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ⚡  Otenga BI Platform — Starting..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Backend ──────────────────────────────────
echo ""
echo "📦  Setting up backend..."
cd "$BACKEND"

if [ ! -d ".venv" ]; then
  echo "   Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt
echo "   ✅  Backend dependencies installed"

# ── Start backend in background ──────────────
echo ""
echo "🚀  Starting FastAPI backend on :8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

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
