# AGENTS.md

## Cursor Cloud specific instructions

### Architecture

Two-service monorepo: Python FastAPI backend (`backend/`) + Vue 3 / Vite frontend (`frontend/`). The frontend proxies `/api` requests to the backend via Vite dev-server config.

### Prerequisites

- **MySQL 8.0** must be running on `localhost:3306` with a database named `cr_platform`.
- **Python 3.12+** with venv at `backend/venv`.
- **Node.js 22+** with npm.

### Starting MySQL (in Cloud Agent container)

MySQL's systemd service does not work inside the container. Start it manually:

```bash
sudo mysqld --user=mysql --datadir=/var/lib/mysql &
sleep 3
```

The default root user password is `root123` (set during initial setup). Connect via TCP: `mysql -u root -proot123 -h 127.0.0.1`.

### Running services

- **Backend**: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000`
- **Frontend**: `cd frontend && npm run dev` (serves on port 3000, proxies `/api` → `:8000`)

### Configuration

Backend reads `backend/.env` (copied from `.env.example`). Key values:
- `DB_HOST=localhost`, `DB_PORT=3306`, `DB_NAME=cr_platform`, `DB_USER=root`, `DB_PASSWORD=root123`
- AI keys (`CURSOR_API_KEY`, `CLAUDE_API_KEY`) are optional; without them the app uses mock data.
- Auth is in mock-bypass mode (`_MOCK_BYPASS = True` in `app/auth.py`), so no token is required for API calls.

### Testing

- `cd backend && source venv/bin/activate && pytest` — no tests exist yet (pytest collects 0 items).
- No ESLint or TypeScript config exists for the frontend; no lint command is configured.

### Build

- Frontend: `cd frontend && npm run build` (outputs to `frontend/dist/`).
- Backend has no build step (runs directly via uvicorn).

### Known gotchas

- The `GET /api/report/{task_id}` endpoint has a Pydantic validation error on the `IssueItem.lines` field when returning mock analysis data — the mock data provides nested lists but the schema expects `List[int]`. This is a pre-existing code issue, not an environment problem.
- MySQL socket-based connections may fail in the container; always use TCP (`-h 127.0.0.1`) for the MySQL client and the `DATABASE_URL` in `.env`.
