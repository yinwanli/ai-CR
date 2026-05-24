# AGENTS.md

## Cursor Cloud specific instructions

### Architecture overview

ai-CR is an AI-assisted code review platform with two services:

| Service | Tech | Port | Run command |
|---------|------|------|-------------|
| Backend | Python 3.12 / FastAPI | 8000 | `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000` |
| Frontend | Vue 3 + Vite | 3000 | `cd frontend && npm run dev` |

The backend requires **MySQL 8.0** on `localhost:3306` with database `cr_platform`.

### Starting MySQL

MySQL must be started manually before the backend:

```bash
sudo mkdir -p /var/run/mysqld && sudo chown mysql:mysql /var/run/mysqld
sudo mysqld_safe --user=mysql &
sleep 3
```

Verify with: `sudo mysql -u root -p'root123' -e "SELECT 1"`

### Backend .env

The backend reads `backend/.env` (copied from `.env.example`). Key values for local dev:

- `DB_PASSWORD=root123`
- `AUTH_TOKEN=demo-token` (use as `X-Auth-Token` header for API calls)
- AI keys (Claude/Cursor) are optional; the app falls back to mock analysis data when unset.

### Running tests

- **Backend**: `cd backend && source venv/bin/activate && python -m pytest -v` (no test files exist yet; exit code 5 = "no tests collected" is expected)
- **Frontend build check**: `cd frontend && npx vite build`

### Lint

No dedicated linter config exists in the repo. Standard Python/JS linting can be applied manually.

### Key gotchas

1. The `database.py` module uses the deprecated `declarative_base()` import from `sqlalchemy.ext.declarative` — this produces a `MovedIn20Warning` but is harmless.
2. The frontend Vite dev server runs on port **3000** (not the Vite default 5173), configured in `vite.config.js`. It proxies `/api` to the backend at `127.0.0.1:8000`.
3. The backend `FRONTEND_URL` in `.env.example` defaults to `http://localhost:5173` but the actual frontend runs on port 3000 — this only affects CORS, and `allow_origins` is permissive enough during development.
4. Analysis tasks use GitHub's public API by default (no token needed for public repos). When no AI keys are configured, the platform uses mock AI analysis results.
