# resustain™ AI — Lean Sustainability Intelligence Platform

AI-powered ESG outreach and engagement platform.
4 services · 10–12s pipeline · Zero Kafka · Zero MongoDB · Zero Pinecone.

---

## Architecture

```
PostgreSQL (pgvector) + Redis + FastAPI + ARQ Worker
```

All 9 AI agent stages run inside a single Python pipeline class.
Pure-function stages execute in microseconds.
I/O stages run concurrently with asyncio.gather.

---

## Quickstart — Demo Mode (no API keys needed)

```bash
# 1. Clone and enter
git clone https://github.com/your-org/treeni-lean.git
cd treeni-lean

# 2. Start frontend only
cd frontend
npm install
npm run dev
# → http://localhost:5173
# → Login: demo@treeni.com / demo123
```

---

## Full Stack (GitHub Codespaces — recommended)

1. Push this repo to GitHub
2. Click **Code → Codespaces → New codespace**
3. Wait ~3 minutes for auto-setup
4. Add your API keys to `backend/.env`
5. Open the forwarded port 5173 in your browser

The `.devcontainer/setup.sh` script runs automatically and:
- Creates Python venv and installs all dependencies
- Waits for PostgreSQL to be ready
- Runs `alembic upgrade head` (creates all tables)
- Installs npm packages

---

## Full Stack (local Docker)

```bash
# 1. Copy env files and add your API keys
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit backend/.env — add at minimum: ANTHROPIC_API_KEY

# 2. Start backend services
docker-compose up -d

# 3. Start frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Switching from Demo to Live

**One line change in `frontend/src/config/index.ts`:**

```typescript
export const USE_MOCK_DATA = false;  // ← change from true to false
```

**Update `frontend/.env`:**
```
VITE_API_BASE_URL=http://localhost:8000
```

Everything automatically routes to the real FastAPI backend.

---

## API Keys — Priority Order

| Key | Get it at | Priority |
|-----|-----------|----------|
| `ANTHROPIC_API_KEY` | console.anthropic.com | Required |
| `OPENAI_API_KEY` | platform.openai.com | Required (embeddings) |
| `SENDGRID_API_KEY` | app.sendgrid.com | Required (email) |
| `ZEROBOUNCE_API_KEY` | zerobounce.net | Required (validation) |
| `APOLLO_API_KEY` | app.apollo.io | Required (contacts) |
| `HUNTER_API_KEY` | hunter.io | High |
| `ENCRYPTION_KEY` | Generate below | Required |
| `RESUSTAIN_API_KEY` | Internal | High |
| `CDP_API_KEY` | cdp.net | Medium |
| `LINKEDIN_ACCESS_TOKEN` | developers.linkedin.com | Optional |
| `WHATSAPP_API_TOKEN` | developers.facebook.com | Optional |

**Generate encryption key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Key Commands

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Restart API after code changes
docker-compose restart api

# Run a prospect pipeline manually
curl -X POST http://localhost:8000/api/prospects/run/sync \
  -H "Content-Type: application/json" \
  -d '{"domain":"bosch.com","persona":"cso","channel":"email"}'

# Check HITL queue
curl http://localhost:8000/api/hitl

# Check agent health
curl http://localhost:8000/health

# Database shell
docker exec -it treeni-postgres psql -U treeni -d treeni_ai

# Reset database (danger!)
docker-compose down -v && docker-compose up -d

# Run migrations manually
cd backend && alembic upgrade head
```

---

## Project Structure

```
treeni-lean/
├── .devcontainer/          Codespaces config + auto-setup script
├── .github/workflows/      CI/CD pipeline (GitHub Actions)
├── docker-compose.yml      4-service stack
│
├── backend/
│   ├── app/
│   │   ├── main.py         FastAPI app — all routes
│   │   ├── pipeline/
│   │   │   └── pipeline.py THE core — all 9 stages in one class
│   │   ├── integrations/
│   │   │   ├── esg_sources.py  6 ESG data sources
│   │   │   ├── contact.py      Apollo + Hunter + ZeroBounce
│   │   │   ├── dispatch.py     SendGrid + LinkedIn + WhatsApp
│   │   │   └── encryption.py   AES-256 PII encryption
│   │   ├── workers/
│   │   │   └── worker.py   ARQ worker — all background jobs
│   │   ├── db/
│   │   │   ├── models.py   SQLAlchemy models + pgvector
│   │   │   └── migrations/ Alembic migration files
│   │   └── core/
│   │       └── settings.py Pydantic settings — all config
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── config/index.ts     USE_MOCK_DATA toggle
    │   ├── mock/data.ts        All demo data
    │   ├── services/api.ts     Mock/live API switch
    │   └── components/         All 8 pages
    ├── package.json
    └── .env.example
```

---

## Pipeline Flow

```
Domain input (e.g. bosch.com)
    ↓
Stage 1+2:  ESG fetch + Firmographics    [parallel, ~3s]
Stage 3+4:  Scoring + Compliance         [pure math, 0.02s]
Stage 5+6:  Contact sourcing + Embedding [parallel, ~2s]
Stage 7:    pgvector similarity search   [1 SQL query, 0.02s]
Stage 8:    Content generation           [LLM, ~6s]
Stage 9:    HITL gate (≥0.75 = send)
Stage 10:   Persist to PostgreSQL
Stage 11:   Dispatch or queue for review
Total:      ~10–12 seconds
```

---

## What's NOT needed (removed from lean version)

- ~~Kafka / Zookeeper~~ → Redis Streams (built into existing Redis)
- ~~MongoDB~~ → PostgreSQL JSONB columns
- ~~Pinecone~~ → pgvector extension on PostgreSQL
- ~~Celery + Flower~~ → ARQ (one file, uses same Redis)
- ~~9 separate agent containers~~ → One pipeline class
- ~~Prometheus + Grafana + Jaeger~~ → Structured logs + Grafana Cloud free tier
- ~~20 running services~~ → 4 running services

---

## Codespaces Deployment

1. Fork this repo
2. Add secrets in **Settings → Secrets → Actions**:
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`
   - `SENDGRID_API_KEY`
   - `ZEROBOUNCE_API_KEY`
   - `APOLLO_API_KEY`
   - `HUNTER_API_KEY`
   - `ENCRYPTION_KEY`
3. Open Codespace → ports 5173 (frontend) and 8000 (API) auto-forward
4. The `USE_MOCK_DATA = true` default means the frontend works immediately
5. Add API keys to `backend/.env` to enable live mode

---

*Version 2.0.0 — Lean Architecture*
*Treeni Sustainability Solutions*
