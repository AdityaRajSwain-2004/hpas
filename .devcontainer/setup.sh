#!/bin/bash
set -e

echo "================================================"
echo "  Treeni AI Platform — Codespaces Setup"
echo "================================================"

# ── Backend setup ─────────────────────────────────
echo ""
echo "→ Setting up Python backend..."
cd /workspace/backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  ✓ Python dependencies installed"

# ── Copy env if not exists ────────────────────────
if [ ! -f /workspace/backend/.env ]; then
  cp /workspace/backend/.env.example /workspace/backend/.env
  echo "  ✓ Created backend/.env from template"
  echo "  ⚠  Add your API keys to backend/.env"
fi

# ── Wait for PostgreSQL ────────────────────────────
echo ""
echo "→ Waiting for PostgreSQL..."
for i in {1..30}; do
  if pg_isready -h localhost -p 5432 -U treeni -q 2>/dev/null; then
    echo "  ✓ PostgreSQL ready"
    break
  fi
  sleep 2
done

# ── Run database migrations ───────────────────────
echo ""
echo "→ Running database migrations..."
cd /workspace/backend
source venv/bin/activate
alembic upgrade head
echo "  ✓ Database schema created"

# ── Frontend setup ────────────────────────────────
echo ""
echo "→ Setting up React frontend..."
cd /workspace/frontend
npm install --silent
echo "  ✓ Node dependencies installed"

if [ ! -f /workspace/frontend/.env ]; then
  cp /workspace/frontend/.env.example /workspace/frontend/.env
  echo "  ✓ Created frontend/.env from template"
fi

echo ""
echo "================================================"
echo "  Setup complete!"
echo ""
echo "  Start backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "  Start worker:   cd backend && source venv/bin/activate && python -m arq app.workers.worker.WorkerSettings"
echo "  Start frontend: cd frontend && npm run dev"
echo ""
echo "  OR use the VS Code tasks (Ctrl+Shift+P → Run Task)"
echo "================================================"
